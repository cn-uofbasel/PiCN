"""Test BasicLinkLayer driven by AsyncRunStrategy (Task 3.3). Mirrors
test_BasicLinkLayer.py's cases exactly, with run_strategy=AsyncRunStrategy()
-- this is ADR-008's literal "two nodes exchange real packets" exit
criterion, for the new path specifically.

BasicLinkLayer's public shape (start_process()/stop_process(), plain
multiprocessing.Queue properties) is unchanged regardless of strategy, so
this test does not itself need to be async -- only what runs inside the
forked child process is.

test_BasicLinkLayer.py is not modified: it characterizes SyncRunStrategy (the
default) and must keep passing unchanged.
"""

import multiprocessing
import socket
import unittest

from PiCN.Layers.LinkLayer.FaceIDTable import FaceIDDict
from PiCN.Layers.LinkLayer.Interfaces import UDP4Interface, AddressInfo
from PiCN.Layers.LinkLayer import BasicLinkLayer
from PiCN.Layers.LinkLayer.RunStrategy import AsyncRunStrategy
from PiCN.Processes import PiCNSyncDataStructFactory


class test_BasicLinkLayer_async(unittest.TestCase):
    """Test BasicLinkLayer with AsyncRunStrategy"""

    def setUp(self):
        self.udp4interface1 = UDP4Interface(0)
        synced_data_struct_factory1 = PiCNSyncDataStructFactory()
        synced_data_struct_factory1.register("faceidtable", FaceIDDict)
        synced_data_struct_factory1.create_manager()
        self.faceidtable1 = synced_data_struct_factory1.manager.faceidtable()
        self.linklayer1 = BasicLinkLayer([self.udp4interface1], self.faceidtable1,
                                          run_strategy=AsyncRunStrategy())
        self.linklayer1.queue_to_higher = multiprocessing.Queue()
        self.linklayer1.queue_from_higher = multiprocessing.Queue()

        self.udp4interface2 = UDP4Interface(0)
        synced_data_struct_factory2 = PiCNSyncDataStructFactory()
        synced_data_struct_factory2.register("faceidtable", FaceIDDict)
        synced_data_struct_factory2.create_manager()
        self.faceidtable2 = synced_data_struct_factory2.manager.faceidtable()
        self.linklayer2 = BasicLinkLayer([self.udp4interface2], self.faceidtable2,
                                          run_strategy=AsyncRunStrategy())
        self.linklayer2.queue_to_higher = multiprocessing.Queue()
        self.linklayer2.queue_from_higher = multiprocessing.Queue()

        self.testSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.testSock.bind(("0.0.0.0", 0))

        self.test_port = self.testSock.getsockname()[1]

    def tearDown(self):
        self.testSock.close()
        self.udp4interface1.close()
        self.udp4interface2.close()
        self.linklayer1.stop_process()
        self.linklayer2.stop_process()

    def test_receiving_a_packet(self):
        """Test if a packet is received correctly, mirroring
        test_BasicLinkLayer.py::test_receiving_a_packet."""
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
        """Test if a packet is sent correctly, mirroring
        test_BasicLinkLayer.py::test_sending_a_packet."""
        self.linklayer1.start_process()
        fid = self.linklayer1.faceidtable.get_or_create_faceid(AddressInfo(("127.0.0.1", self.test_port),
                                                                           self.linklayer1.interfaces.index(
                                                                              self.udp4interface1)))
        self.linklayer1.queue_from_higher.put([fid, "HelloWorld".encode()])

        data, addr = self.testSock.recvfrom(8192)
        self.assertEqual(data.decode(), "HelloWorld")

    def test_sending_and_receiving_a_packet(self):
        """Test sending/receiving in a single case, mirroring
        test_BasicLinkLayer.py::test_sending_and_receiving_a_packet -- two
        AsyncRunStrategy-driven nodes exchanging a real packet."""
        self.linklayer1.start_process()
        self.linklayer2.start_process()

        fid = self.linklayer1.faceidtable.get_or_create_faceid(AddressInfo(("127.0.0.1", self.udp4interface2.get_port()),
                                                                           self.linklayer1.interfaces.index(
                                                                              self.udp4interface1)))
        self.linklayer1.queue_from_higher.put([fid, "HelloWorld".encode()])

        data = self.linklayer2.queue_to_higher.get(timeout=2.0)
        faceid = data[0]
        packet = data[1]

        self.assertEqual(faceid, 0)
        self.assertEqual(packet.decode(), "HelloWorld")


if __name__ == "__main__":
    unittest.main()
