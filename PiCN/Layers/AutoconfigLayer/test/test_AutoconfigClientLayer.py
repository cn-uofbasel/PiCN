
import unittest
import multiprocessing
import socket

from datetime import datetime, timedelta
import queue

from PiCN.Layers.AutoconfigLayer import AutoconfigClientLayer
from PiCN.Packets import Name, Interest, Content, Nack, NackReason

from PiCN.Layers.AutoconfigLayer.test.mocks import MockLinkLayer


class test_AutoconfigClientLayer(unittest.TestCase):

    def setUp(self):
        self.manager = multiprocessing.Manager()
        self.linklayer_mock = MockLinkLayer(port=1337)
        self.autoconflayer = AutoconfigClientLayer(linklayer=self.linklayer_mock,
                                                   bcaddr='127.255.255.255', bcport=4242,
                                                   solicitation_timeout=3.0)
        self.autoconflayer.queue_to_higher = self.queue_to_higher = multiprocessing.Queue()
        self.autoconflayer.queue_from_higher = self.queue_from_higher = multiprocessing.Queue()
        self.autoconflayer.queue_to_lower = self.queue_to_lower = multiprocessing.Queue()
        self.autoconflayer.queue_from_lower = self.queue_from_lower = multiprocessing.Queue()

    def tearDown(self):
        self.autoconflayer.stop_process()
        self.queue_to_higher.close()
        self.queue_from_higher.close()
        self.queue_to_lower.close()
        self.queue_from_lower.close()

    def test_broadcast_enabled(self):
        """Test that broadcasting was enabled on the UDP socket"""
        self.autoconflayer.start_process()
        self.linklayer_mock.sock.setsockopt.assert_called_once_with(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    def test_pass_through(self):
        """Test that autoconfig-unrelated content is passed through unchanged"""
        self.autoconflayer.start_process()
        # Pass an interest object from below
        interest = Interest(Name('/foo/bar'))
        self.queue_from_lower.put([42, interest])
        data = self.queue_to_higher.get()
        self.assertEqual(2, len(data))
        self.assertEqual(42, data[0])
        self.assertEqual(interest, data[1])
        # Pass a content object from above
        content = Content(Name('/foo/bar'), 'foo bar')
        self.queue_from_higher.put([1337, content])
        data = self.queue_to_lower.get()
        self.assertEqual(2, len(data))
        self.assertEqual(1337, data[0])
        self.assertEqual(content, data[1])

    def test_forwarder_solicitation_sent(self):
        """Test that a forwarder solicitation is sent"""
        waittime = 3.0
        self.autoconflayer.start_process()
        # Pass an interest to the autoconfig layer to trigger forwarder solicitation
        interest = Interest(Name('/foo/bar'))
        self.queue_from_higher.put([None, interest])

        # Catch all data the autoconfig layer sends downwards for 3 seconds
        deadline = datetime.utcnow() + timedelta(seconds=waittime)
        tolower = []
        while datetime.utcnow() < deadline:
            try:
                data = self.queue_to_lower.get(timeout=waittime/10)
                tolower.append(data)
            except queue.Empty:
                pass
        # Make sure the broadcast face was actually created and get its face id
        bcfid = self.linklayer_mock._ip_to_fid.get(('127.255.255.255', 4242), None)
        self.assertIsNotNone(bcfid)
        # Make sure a forwarder solicitation was sent downwards
        solictiation = Interest(Name('/autoconfig/forwarders'))
        self.assertIn([bcfid, solictiation], tolower)

    def test_interest_passed_down_after_advertiesement(self):
        """
        Test that held interests are passed downwards once a forwarder advertisement with a matching route is received.
        """
        waittime = 3.0
        self.autoconflayer.start_process()
        # Create some test interests, two with the advertised prefix, and one with another
        foobar = Interest(Name('/foo/bar'))
        foobaz = Interest(Name('/foo/bar'))
        barfoo = Interest(Name('/bar/foo'))
        self.queue_from_higher.put([None, foobar])
        self.queue_from_higher.put([None, foobaz])
        self.queue_from_higher.put([None, barfoo])

        # Catch all data the autoconfig layer sends downwards for 3 seconds
        deadline = datetime.utcnow() + timedelta(seconds=waittime)
        tolower = []
        while datetime.utcnow() < deadline:
            try:
                data = self.queue_to_lower.get(timeout=waittime/10)
                tolower.append(data)
            except queue.Empty:
                pass
        # Make sure the broadcast face was actually created and get its face id
        bcfid = self.linklayer_mock._ip_to_fid.get(('127.255.255.255', 4242), None)
        self.assertIsNotNone(bcfid)
        # Make sure a forwarder solicitation was sent downwards
        solictiation = Interest(Name('/autoconfig/forwarders'))
        self.assertIn([bcfid, solictiation], tolower)

        # Create a forwarder advertisement and pass it to the autoconfig layer
        advertisement = Content(Name('/autoconfig/forwarders'), '127.13.37.42:1234\nr:/foo\n')
        self.queue_from_lower.put([bcfid, advertisement])
        # Catch all data the autoconfig layer sends downwards for 3 seconds
        deadline = datetime.utcnow() + timedelta(seconds=waittime)
        tolower = []
        while datetime.utcnow() < deadline:
            try:
                data = self.queue_to_lower.get(timeout=waittime/10)
                tolower.append(data)
            except queue.Empty:
                pass
        # Make sure the face to the forwarder was actually created and get its face id
        fwdfid = self.linklayer_mock._ip_to_fid.get(('127.13.37.42', 1234), None)
        self.assertIsNotNone(fwdfid)
        # Make sure the two interests with matching prefixes were passed downwards
        self.assertIn([fwdfid, foobar], tolower)
        self.assertIn([fwdfid, foobaz], tolower)
        self.assertNotIn([fwdfid, barfoo], tolower)

    def test_solicitation_no_reply_resend(self):
        """Test whether a forwarder solicitation is resent if no reply is received"""
        waittime = self.autoconflayer._solicitation_timeout * 4.0
        self.autoconflayer.start_process()
        interest = Interest(Name('/foo/bar'))
        self.queue_from_higher.put([None, interest])

        # Catch all data the autoconfig layer sends downwards for 3 seconds
        deadline = datetime.utcnow() + timedelta(seconds=waittime)
        tolower = []
        while datetime.utcnow() < deadline:
            try:
                data = self.queue_to_lower.get(timeout=waittime/10)
                tolower.append(data)
            except queue.Empty:
                pass
        # Make sure the broadcast face was actually created and get its face id
        bcfid = self.linklayer_mock._ip_to_fid.get(('127.255.255.255', 4242), None)
        self.assertIsNotNone(bcfid)
        # Make sure the forwarder solicitation was sent more than once
        solictiation = Interest(Name('/autoconfig/forwarders'))
        solictiation_count = len([1 for data in tolower if data == [bcfid, solictiation]])
        self.assertGreater(solictiation_count, 1)

    def test_solicitation_max_retry(self):
        """Test that solicitations are not retried ad infinitum and a Nack NO_ROUTE is sent upwards after the timeout"""
        self.autoconflayer._solicitation_max_retry = 6
        waittime = self.autoconflayer._solicitation_timeout * 10
        self.autoconflayer.start_process()
        interest = Interest(Name('/foo/bar'))
        self.queue_from_higher.put([None, interest])

        deadline = datetime.utcnow() + timedelta(seconds=waittime)
        tolower = []
        while datetime.utcnow() < deadline:
            try:
                data = self.queue_to_lower.get(timeout=waittime/10)
                tolower.append(data)
            except queue.Empty:
                pass
        tohigher = self.queue_to_higher.get(timeout=waittime/10)
        bcfid = self.linklayer_mock._ip_to_fid.get(('127.255.255.255', 4242), None)
        self.assertIsNotNone(bcfid)
        solictiation = Interest(Name('/autoconfig/forwarders'))
        solictiation_count = len([1 for data in tolower if data == [bcfid, solictiation]])
        self.assertEqual(6, solictiation_count)
        self.assertIsNone(tohigher[0])
        self.assertIsInstance(tohigher[1], Nack)
        self.assertEqual('/foo/bar', tohigher[1].name.components_to_string())
        self.assertEqual(NackReason.NO_ROUTE, tohigher[1].reason)
