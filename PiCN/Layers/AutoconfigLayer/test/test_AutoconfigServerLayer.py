
import unittest
import multiprocessing
import socket

from typing import List

from PiCN.Layers.AutoconfigLayer import AutoconfigServerLayer
from PiCN.Layers.ICNLayer.ForwardingInformationBase import ForwardingInformationBaseMemoryPrefix
from PiCN.Packets import Name, Interest, Content, Nack, NackReason

from PiCN.Layers.AutoconfigLayer.test.mocks import MockLinkLayer


class test_AutoconfigServerLayer(unittest.TestCase):

    def setUp(self):
        self.manager = multiprocessing.Manager()
        self.linklayer_mock = MockLinkLayer(port=1337)
        self.fib = ForwardingInformationBaseMemoryPrefix(self.manager)
        outfid = self.linklayer_mock._get_or_create_fid(('127.13.37.42', 4242))
        self.fib.add_fib_entry(Name('/global'), outfid)
        self.prefixes: List[Name] = [Name('/test/repos'), Name('/home')]
        self.autoconflayer = AutoconfigServerLayer(linklayer=self.linklayer_mock, fib=self.fib, address='127.0.1.1',
                                                   broadcast='127.255.255.255',
                                                   registration_prefixes=self.prefixes)
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
        interest = Interest(Name('/foo/bar'))
        self.queue_from_lower.put([42, interest])
        data = self.queue_to_higher.get()
        self.assertEqual(2, len(data))
        self.assertEqual(42, data[0])
        self.assertEqual(interest, data[1])
        content = Content(Name('/foo/bar'), 'foo bar')
        self.queue_from_higher.put([1337, content])
        data = self.queue_to_lower.get()
        self.assertEqual(2, len(data))
        self.assertEqual(1337, data[0])
        self.assertEqual(content, data[1])

    def test_get_forwarder_info(self):
        """Test simple retrieval of the forwarder info"""
        self.autoconflayer.start_process()
        name = Name('/autoconfig/forwarders')
        interest = Interest(name)
        self.queue_from_lower.put([42, interest])
        fid, packet = self.queue_to_lower.get()
        self.assertEqual(42, fid)
        self.assertIsInstance(packet, Content)
        self.assertEqual(name, packet.name)
        lines: List[str] = [line for line in packet.content.split('\n') if len(line) > 0]
        self.assertEqual(4, len(lines))
        self.assertEqual('127.0.1.1:1337', lines[0])
        self.assertIn('r:/global', lines)
        self.assertIn('p:/test/repos', lines)
        self.assertIn('p:/home', lines)

    def test_register_service(self):
        """Test service registration and subsequent retrieval of the service list"""
        self.autoconflayer.start_process()
        rname = Name('/autoconfig/service/127.42.42.42:1337/test/repos/testrepo')
        rinterest = Interest(rname)
        self.queue_from_lower.put([42, rinterest])
        fid, packet = self.queue_to_lower.get()
        self.assertEqual(42, fid)
        self.assertIsInstance(packet, Content)
        self.assertEqual(rname, packet.name)
        lname = Name('/autoconfig/services')
        linterest = Interest(lname)
        self.queue_from_lower.put([42, linterest])
        fid, packet = self.queue_to_lower.get()
        self.assertEqual(42, fid)
        self.assertIsInstance(packet, Content)
        self.assertEqual(lname, packet.name)
        lines: List[str] = [line for line in packet.content.split('\n') if len(line) > 0]
        self.assertIn('/test/repos/testrepo', lines)

    def test_reregister_service(self):
        """Test re-registration of a service with matching name and address"""
        self.autoconflayer.start_process()
        rname = Name('/autoconfig/service/127.42.42.42:1337/test/repos/testrepo')
        rinterest = Interest(rname)
        for i in range(2):
            self.queue_from_lower.put([42, rinterest])
            fid, packet = self.queue_to_lower.get()
            self.assertEqual(42, fid)
            self.assertIsInstance(packet, Content)
            self.assertEqual(rname, packet.name)

    def test_register_service_twice_different_addr_nack(self):
        """Test registration of a second service with a different address under the same name; should be refused"""
        self.autoconflayer.start_process()
        rname = Name('/autoconfig/service/127.42.42.42:1337/test/repos/testrepo')
        rinterest = Interest(rname)
        self.queue_from_lower.put([42, rinterest])
        fid, packet = self.queue_to_lower.get()
        self.assertEqual(42, fid)
        self.assertIsInstance(packet, Content)
        self.assertEqual(rname, packet.name)
        fname = Name('/autoconfig/service/127.0.0.42:1337/test/repos/testrepo')
        finterest = Interest(fname)
        self.queue_from_lower.put([42, finterest])
        fid, packet = self.queue_to_lower.get()
        self.assertEqual(42, fid)
        self.assertIsInstance(packet, Nack)
        self.assertEqual(NackReason.DUPLICATE, packet.reason)
        self.assertEqual(fname, packet.name)

    def test_register_service_unavailable_prefix_nack(self):
        """Test registration of a service under a prefix that is not advertised by the forwarder; should be refused"""
        self.autoconflayer.start_process()
        self.autoconflayer.start_process()
        rname = Name('/autoconfig/service/127.42.42.42:1337/otherprefix/testrepo')
        rinterest = Interest(rname)
        self.queue_from_lower.put([42, rinterest])
        fid, packet = self.queue_to_lower.get()
        self.assertEqual(42, fid)
        self.assertIsInstance(packet, Nack)
        self.assertEqual(rname, packet.name)
        self.assertEqual(packet.reason, NackReason.NO_ROUTE)
