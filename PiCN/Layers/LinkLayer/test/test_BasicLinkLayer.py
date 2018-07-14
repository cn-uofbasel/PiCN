"""Test the Basic Link Layer"""

import multiprocessing
import socket
import unittest

from PiCN.Layers.LinkLayer import BasicLinkLayer
from PiCN.Layers.LinkLayer.FaceIDTable import FaceIDDict
from PiCN.Layers.LinkLayer.Interfaces import UDP4Interface, AddressInfo
from PiCN.Processes import PiCNSyncDataStructFactory


class test_BasicLinkLayer(unittest.TestCase):
    """Test the Basic Link Layer"""

    def setUp(self):
        self.udp4interface1 = UDP4Interface(0)
        synced_data_struct_factory1 = PiCNSyncDataStructFactory()
        synced_data_struct_factory1.register("faceidtable", FaceIDDict)
        synced_data_struct_factory1.create_manager()
        self.faceidtable1 = synced_data_struct_factory1.manager.faceidtable()
        self.linklayer1 = BasicLinkLayer([self.udp4interface1], self.faceidtable1)
        self.linklayer1.queue_to_higher = multiprocessing.Queue()
        self.linklayer1.queue_from_higher = multiprocessing.Queue()

        self.udp4interface2 = UDP4Interface(0)
        synced_data_struct_factory2 = PiCNSyncDataStructFactory()
        synced_data_struct_factory2.register("faceidtable", FaceIDDict)
        synced_data_struct_factory2.create_manager()
        self.faceidtable2 = synced_data_struct_factory2.manager.faceidtable()
        self.linklayer2 = BasicLinkLayer([self.udp4interface2], self.faceidtable2)
        self.linklayer2.queue_to_higher = multiprocessing.Queue()
        self.linklayer2.queue_from_higher = multiprocessing.Queue()

        self.udp4interface3 = UDP4Interface(0)
        synced_data_struct_factory3 = PiCNSyncDataStructFactory()
        synced_data_struct_factory3.register("faceidtable", FaceIDDict)
        synced_data_struct_factory3.create_manager()
        self.faceidtable3 = synced_data_struct_factory3.manager.faceidtable()
        self.linklayer3 = BasicLinkLayer([self.udp4interface3], self.faceidtable3)
        self.linklayer3.queue_to_higher = multiprocessing.Queue()
        self.linklayer3.queue_from_higher = multiprocessing.Queue()

        self.testSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.testSock.bind(("0.0.0.0", 0))

        self.test_port = self.testSock.getsockname()[1]

    def tearDown(self):
        self.udp4interface1.close()
        self.udp4interface2.close()
        self.linklayer1.stop_process()
        self.linklayer2.stop_process()

    def test_receiving_a_packet(self):
        """Test if a packet is received correctly"""
        self.linklayer1.start_process()
        self.testSock.sendto("HelloWorld".encode(), ("127.0.0.1", self.udp4interface1.get_port()))

        data = self.linklayer1.queue_to_higher.get(timeout=2.0)
        faceid = data[0]
        content = data[1].decode()
        self.assertEqual("HelloWorld", content)
        self.assertEqual(self.linklayer1.faceidtable.get_num_entries(), 1)
        self.assertEqual(self.linklayer1.faceidtable.get_address_info(0).address[1], self.test_port)
        self.assertEqual(self.linklayer1.faceidtable.get_address_info(0).interface_id, 0)

    def test_sending_a_packet(self):
        """Test if a packet is sent correctly"""
        self.linklayer1.start_process()
        fid = self.linklayer1.faceidtable.get_or_create_faceid(AddressInfo(("127.0.0.1", self.test_port),
                                                                           self.linklayer1.interfaces.index(
                                                                               self.udp4interface1)))
        self.linklayer1.queue_from_higher.put([fid, "HelloWorld".encode()])

        data, addr = self.testSock.recvfrom(8192)
        self.assertEqual(data.decode(), "HelloWorld")

    def test_sending_and_receiving_a_packet(self):
        """Test sending/receiving in a single case"""
        self.linklayer1.start_process()
        self.linklayer2.start_process()

        fid = self.linklayer1.faceidtable.get_or_create_faceid(
            AddressInfo(("127.0.0.1", self.udp4interface2.get_port()),
                        self.linklayer1.interfaces.index(
                            self.udp4interface1)))
        self.linklayer1.queue_from_higher.put([fid, "HelloWorld".encode()])

        data = self.linklayer2.queue_to_higher.get(timeout=2.0)
        faceid = data[0]
        packet = data[1]

        self.assertEqual(faceid, 0)
        self.assertEqual(packet.decode(), "HelloWorld")

    def test_sending_and_receiving_packets(self):
        """Test sending/receiving many packets in a single case"""

        self.linklayer1.start_process()
        self.linklayer2.start_process()

        fid1 = self.linklayer1.faceidtable.get_or_create_faceid(
            AddressInfo(("127.0.0.1", self.udp4interface2.get_port()),
                        self.linklayer1.interfaces.index(
                            self.udp4interface1)))
        self.linklayer1.start_process()
        self.linklayer2.start_process()

        fid2 = self.linklayer2.faceidtable.get_or_create_faceid(
            AddressInfo(("127.0.0.1", self.udp4interface1.get_port()),
                        self.linklayer2.interfaces.index(
                            self.udp4interface2)))

        for i in range(1, int(1e3)):
            str1 = "HelloWorld" + str(i)
            str2 = "GoodBye" + str(i)

            self.linklayer1.queue_from_higher.put([fid1, str1.encode()])
            self.linklayer2.queue_from_higher.put([fid2, str2.encode()])

            d2 = self.linklayer2.queue_to_higher.get(timeout=2.0)
            d1 = self.linklayer1.queue_to_higher.get(timeout=2.0)

            packet2 = d1[1].decode()
            packet1 = d2[1].decode()

            self.assertEqual(packet1, str1)
            self.assertEqual(packet2, str2)

        for i in range(1, int(1e3)):
            str1 = "HelloWorld" + str(i)
            str2 = "GoodBye" + str(i)

            self.linklayer1.queue_from_higher.put([fid1, str1.encode()])
            self.linklayer2.queue_from_higher.put([fid2, str2.encode()])

            d1 = self.linklayer1.queue_to_higher.get(timeout=2.0)
            d2 = self.linklayer2.queue_to_higher.get(timeout=2.0)

            packet2 = d1[1].decode()
            packet1 = d2[1].decode()

            self.assertEqual(packet1, str1)
            self.assertEqual(packet2, str2)

    def test_sending_and_receiving_pacets_three_nodes(self):
        """Testing sending/receiving packets with three nodes"""
        self.linklayer1.start_process()
        self.linklayer2.start_process()
        self.linklayer3.start_process()

        fid1_2 = self.linklayer1.faceidtable.get_or_create_faceid(
            AddressInfo(("127.0.0.1", self.udp4interface2.get_port()),
                        self.linklayer1.interfaces.index(self.udp4interface1)))
        fid1_3 = self.linklayer1.faceidtable.get_or_create_faceid(
            AddressInfo(("127.0.0.1", self.udp4interface3.get_port()),
                        self.linklayer1.interfaces.index(self.udp4interface1)))

        fid2_1 = self.linklayer2.faceidtable.get_or_create_faceid(
            AddressInfo(("127.0.0.1", self.udp4interface1.get_port()),
                        self.linklayer2.interfaces.index(self.udp4interface2)))

        fid3_1 = self.linklayer3.faceidtable.get_or_create_faceid(
            AddressInfo(("127.0.0.1", self.udp4interface1.get_port()),
                        self.linklayer3.interfaces.index(self.udp4interface3)))
        fid3_2 = self.linklayer3.faceidtable.get_or_create_faceid(
            AddressInfo(("127.0.0.1", self.udp4interface2.get_port()),
                        self.linklayer3.interfaces.index(self.udp4interface3)))

        for i in range(1, 100):
            str1 = "Node1" + str(i)
            str2 = "Node2" + str(i)
            str3 = "Node3" + str(i)

            # Node 1 ---> Node 2
            self.linklayer1.queue_from_higher.put([fid1_2, str1.encode()])
            try:
                data1_2 = self.linklayer2.queue_to_higher.get(timeout=2.0)
            except:
                self.fail()
            # Node 1 ---> Node 3
            self.linklayer1.queue_from_higher.put([fid1_3, str1.encode()])
            try:
                data1_3 = self.linklayer3.queue_to_higher.get(timeout=2.0)
            except:
                self.fail()
            # Node 2 ---> Node 1
            self.linklayer2.queue_from_higher.put([fid2_1, str2.encode()])
            try:
                data2_1 = self.linklayer1.queue_to_higher.get(timeout=2.0)
            except:
                self.fail()
            # Node 3 ---> Node 1
            self.linklayer3.queue_from_higher.put([fid3_1, str3.encode()])
            try:
                data3_1 = self.linklayer1.queue_to_higher.get(timeout=2.0)
            except:
                self.fail()
            # Node 3 ---> Node 2
            self.linklayer3.queue_from_higher.put([fid3_2, str3.encode()])
            try:
                data3_2 = self.linklayer2.queue_to_higher.get(timeout=2.0)
            except:
                self.fail()

            self.assertEqual(data1_2[1].decode(), str1)
            self.assertEqual(data1_3[1].decode(), str1)
            self.assertEqual(data2_1[1].decode(), str2)
            self.assertEqual(data3_1[1].decode(), str3)
            self.assertEqual(data3_2[1].decode(), str3)
