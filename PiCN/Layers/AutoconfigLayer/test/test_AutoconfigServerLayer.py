
import unittest
import multiprocessing
import socket

from typing import List, Tuple

from PiCN.Layers.AutoconfigLayer import AutoconfigServerLayer
from PiCN.Layers.ICNLayer.ForwardingInformationBase import ForwardingInformationBaseMemoryPrefix
from PiCN.Layers.LinkLayer import BasicLinkLayer
from PiCN.Layers.LinkLayer.FaceIDTable import FaceIDDict
from PiCN.Layers.LinkLayer.Interfaces import AddressInfo
from PiCN.Packets import Name, Interest, Content, Nack, NackReason

from PiCN.Layers.AutoconfigLayer.test.mocks import MockInterface
from PiCN.Processes import PiCNSyncDataStructFactory


class test_AutoconfigServerLayer(unittest.TestCase):

    def setUp(self):
        synced_data_struct_factory = PiCNSyncDataStructFactory()
        synced_data_struct_factory.register('fib', ForwardingInformationBaseMemoryPrefix)
        synced_data_struct_factory.register('faceidtable', FaceIDDict)
        synced_data_struct_factory.create_manager()
        fib = synced_data_struct_factory.manager.fib()
        self.faceidtable: FaceIDDict = synced_data_struct_factory.manager.faceidtable()
        # Create a face and an example route
        self.mock_interface = MockInterface(port=1337)
        self.linklayer = BasicLinkLayer([self.mock_interface], self.faceidtable)

        outfid = self.linklayer.faceidtable.get_or_create_faceid(AddressInfo(('127.13.37.42', 4242), 0))
        fib.add_fib_entry(Name('/global'), outfid)
        # List of advertised prefixes
        self.prefixes: List[Tuple[Name, bool]] = [(Name('/test/repos'), False), (Name('/home'), True)]
        self.autoconflayer = AutoconfigServerLayer(linklayer=self.linklayer,
                                                   address='127.0.1.1',
                                                   registration_prefixes=self.prefixes)
        self.autoconflayer.fib = fib
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
        self.mock_interface.sock.setsockopt.assert_called_once_with(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    def test_pass_through(self):
        """Test that autoconfig-unrelated content is passed through unchanged"""
        self.autoconflayer.start_process()
        # Pass an interest object from below
        interest = Interest(Name('/foo/bar'))
        self.faceidtable.add(42, AddressInfo(('127.13.37.42', 4567), 0))
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

    def test_get_forwarder_advertisement(self):
        """Test simple retrieval of the forwarder advertisement"""
        self.autoconflayer.start_process()
        # Send forwarder solicitation
        name = Name('/autoconfig/forwarders')
        interest = Interest(name)
        self.faceidtable.add(42, AddressInfo(('127.13.37.42', 4567), 0))
        self.queue_from_lower.put([42, interest])
        # Receive forwarder advertisement
        fid, packet = self.queue_to_lower.get()
        self.assertEqual(42, fid)
        self.assertIsInstance(packet, Content)
        self.assertEqual(name, packet.name)
        lines: List[str] = [line for line in packet.content.split('\n') if len(line) > 0]
        self.assertEqual(4, len(lines))
        self.assertEqual('udp4://127.0.1.1:1337', lines[0])
        self.assertIn('r:/global', lines)
        self.assertIn('pg:/test/repos', lines)
        self.assertIn('pl:/home', lines)

    def test_register_service(self):
        """Test service registration and subsequent retrieval of the service list"""
        self.autoconflayer.start_process()
        # Send service registration
        rname = Name('/autoconfig/service')
        rname += 'udp4://127.42.42.42:1337'
        rname += 'test'
        rname += 'repos'
        rname += 'testrepo'
        rinterest = Interest(rname)
        self.faceidtable.add(42, AddressInfo(('127.13.37.42', 4567), 0))
        self.queue_from_lower.put([42, rinterest])
        # Receive service registration ACK
        fid, packet = self.queue_to_lower.get()
        self.assertEqual(42, fid)
        self.assertIsInstance(packet, Content)
        self.assertEqual(rname, packet.name)
        # Request known services list
        lname = Name('/autoconfig/services')
        linterest = Interest(lname)
        self.queue_from_lower.put([42, linterest])
        # Receive known services list
        fid, packet = self.queue_to_lower.get()
        self.assertEqual(42, fid)
        self.assertIsInstance(packet, Content)
        self.assertEqual(lname, packet.name)
        lines: List[str] = [line for line in packet.content.split('\n') if len(line) > 0]
        self.assertIn('/test/repos/testrepo', lines)

    def test_reregister_service(self):
        """Test re-registration of a service with matching name and address"""
        self.autoconflayer.start_process()
        rname = Name('/autoconfig/service')
        rname += 'udp4://127.42.42.42:1337'
        rname += 'test'
        rname += 'repos'
        rname += 'testrepo'
        rinterest = Interest(rname)
        for i in range(2):
            # Send service registration
            self.faceidtable.add(42, AddressInfo(('127.13.37.42', 4567), 0))
            self.queue_from_lower.put([42, rinterest])
            # Receive service registration, should be ACK both times
            fid, packet = self.queue_to_lower.get()
            self.assertEqual(42, fid)
            self.assertIsInstance(packet, Content)
            self.assertEqual(rname, packet.name)

    def test_register_service_twice_different_addr_nack(self):
        """Test registration of a second service with a different address under the same name; should be refused"""
        self.autoconflayer.start_process()
        # Send first service registration
        rname = Name('/autoconfig/service')
        rname += 'udp4://127.42.42.42:1337'
        rname += 'test'
        rname += 'repos'
        rname += 'testrepo'
        rinterest = Interest(rname)
        self.faceidtable.add(42, AddressInfo(('127.13.37.42', 4567), 0))
        self.queue_from_lower.put([42, rinterest])
        # Receive first service registration reply, should be ACK
        fid, packet = self.queue_to_lower.get()
        self.assertEqual(42, fid)
        self.assertIsInstance(packet, Content)
        self.assertEqual(rname, packet.name)
        # Send second service registration with different address
        fname = Name('/autoconfig/service')
        fname += 'udp4://127.0.0.42:1337'
        fname += 'test'
        fname += 'repos'
        fname += 'testrepo'
        finterest = Interest(fname)
        self.queue_from_lower.put([42, finterest])
        # Receive second service registration reply, should be NACK
        fid, packet = self.queue_to_lower.get()
        self.assertEqual(42, fid)
        self.assertIsInstance(packet, Nack)
        self.assertEqual(NackReason.DUPLICATE, packet.reason)
        self.assertEqual(fname, packet.name)

    def test_register_service_unavailable_prefix_nack(self):
        """Test registration of a service under a prefix that is not advertised by the forwarder; should be refused"""
        self.autoconflayer.start_process()
        # Send service registration with non-advertised name
        rname = Name('/autoconfig/service')
        rname += 'udp4://127.42.42.42:1337'
        rname += 'otherprefix'
        rname += 'testrepo'
        rinterest = Interest(rname)
        self.faceidtable.add(42, AddressInfo(('127.13.37.42', 4567), 0))
        self.queue_from_lower.put([42, rinterest])
        # Receive service registration reply, should be NACK
        fid, packet = self.queue_to_lower.get()
        self.assertEqual(42, fid)
        self.assertIsInstance(packet, Nack)
        self.assertEqual(rname, packet.name)
        self.assertEqual(packet.reason, NackReason.NO_ROUTE)
