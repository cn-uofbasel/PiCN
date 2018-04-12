
import unittest
import multiprocessing
import socket
import time
import queue
from datetime import datetime, timedelta

from PiCN.Layers.AutoconfigLayer import AutoconfigRepoLayer
from PiCN.Packets import Name, Interest, Content, Nack, NackReason

from PiCN.Layers.AutoconfigLayer.test.mocks import MockLinkLayer, MockRepository


class test_AutoconfigRepoLayer(unittest.TestCase):

    def setUp(self):
        self.manager = multiprocessing.Manager()
        self.linklayer_mock = MockLinkLayer(port=1337)
        self.repo = MockRepository(Name('/unconfigured'))
        self.autoconflayer = AutoconfigRepoLayer(name='testrepo', linklayer=self.linklayer_mock, repo=self.repo,
                                                 addr='127.0.1.1', port=4242, bcaddr='127.255.255.255', bcport=4242)
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

    def test_initial_forwarder_solicitation(self):
        """Test that the autoconfig layer sends an initial forwarder solicitation when starting"""
        self.autoconflayer.start_process()
        # Receive forwarder solicitation
        data = self.queue_to_lower.get()
        self.assertEqual(2, len(data))
        self.assertIsInstance(data[0], int)
        self.assertIsInstance(data[1], Interest)
        self.assertEqual(Name('/autoconfig/forwarders'), data[1].name)

    def test_pass_through(self):
        """Test that autoconfig-unrelated content is passed through unchanged"""
        self.autoconflayer.start_process()
        # Receive forwarder solicitation
        _ = self.queue_to_lower.get()
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

    def test_service_registration(self):
        """Test that a service registration interest is sent"""
        self.autoconflayer.start_process()
        # Receive forwarder solicitation
        bface, _ = self.queue_to_lower.get()
        # Send forwarder advertisement
        forwarders = Content(Name('/autoconfig/forwarders'), 'udp4://127.42.42.42:9000\nr:/global\npl:/test\n')
        self.queue_from_lower.put([42, forwarders])
        # Receive service registration
        fid, data = self.queue_to_lower.get()
        self.assertEqual(bface, fid)
        self.assertIsInstance(data, Interest)
        registration_name = Name('/autoconfig/service')
        registration_name += 'udp4://127.0.1.1:4242'
        registration_name += 'test'
        registration_name += 'testrepo'
        self.assertEqual(registration_name, data.name)

    def test_service_registration_prefix_changed(self):
        """Test that a service registration interest is sent"""
        self.autoconflayer.start_process()
        # Receive forwarder solicitation
        bface, _ = self.queue_to_lower.get()
        # Send forwarder advertisement
        forwarders = Content(Name('/autoconfig/forwarders'), 'udp4://127.42.42.42:9000\nr:/global\npl:/test\n')
        self.queue_from_lower.put([42, forwarders])
        # Receive service registration
        fid, data = self.queue_to_lower.get()
        registration_name = Name('/autoconfig/service')
        registration_name += 'udp4://127.0.1.1:4242'
        registration_name += 'test'
        registration_name += 'testrepo'
        self.assertEqual(registration_name, data.name)
        # Send service registration ACK
        content = Content(registration_name, '3600\n')
        self.queue_from_lower.put([42, content])
        time.sleep(1)
        # Make sure the repo prefix was changed
        self.assertEqual(Name('/test/testrepo'), self.repo.prefix.value)

    def test_service_registration_nack_prefix_not_changed(self):
        """Test that a service registration interest is sent"""
        self.autoconflayer.start_process()
        # Receive forwarder solicitation
        bface, _ = self.queue_to_lower.get()
        # Send forwarder advertisement
        forwarders = Content(Name('/autoconfig/forwarders'), 'udp4://127.42.42.42:9000\nr:/global\npl:/test\n')
        self.queue_from_lower.put([42, forwarders])
        # Receive service registration
        fid, data = self.queue_to_lower.get()
        registration_name = Name('/autoconfig/service')
        registration_name += 'udp4://127.0.1.1:4242'
        registration_name += 'test'
        registration_name += 'testrepo'
        self.assertEqual(registration_name, data.name)
        # Send service registration NACK
        nack = Nack(registration_name, NackReason.NO_ROUTE)
        self.queue_from_lower.put([42, nack])
        time.sleep(1)
        # Make sure the repo prefix was NOT changed
        self.assertEqual(Name('/unconfigured'), self.repo.prefix.value)

    def test_service_registration_timeout_renewal(self):
        """Test that the service registration is renewed before the timeout"""
        waittime = 5
        self.autoconflayer.start_process()
        # Receive forwarder solicitation
        bface, _ = self.queue_to_lower.get()
        # Send forwarder advertisement
        forwarders = Content(Name('/autoconfig/forwarders'), 'udp4://127.42.42.42:9000\nr:/global\npl:/test\n')
        self.queue_from_lower.put([42, forwarders])
        # Receive service registration
        fid, data = self.queue_to_lower.get()
        registration_name = Name('/autoconfig/service')
        registration_name += 'udp4://127.0.1.1:4242'
        registration_name += 'test'
        registration_name += 'testrepo'
        self.assertEqual(registration_name, data.name)
        # Send service registration ACK with a ridiculously short timeout
        content = Content(registration_name, f'{waittime}\n')
        self.queue_from_lower.put([42, content])
        # Catch all data the autoconfig layer sends downwards for 5 seconds
        data = []
        timeout = datetime.utcnow() + timedelta(seconds=waittime)
        while datetime.utcnow() < timeout:
            try:
                data.append(self.queue_to_lower.get(timeout=waittime/10))
            except queue.Empty:
                pass
        registration_interest = Interest(registration_name)
        self.assertIn([bface, registration_interest], data)
