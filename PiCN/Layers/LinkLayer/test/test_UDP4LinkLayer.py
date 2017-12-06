"""Test the UDP4LinkLayer"""

import socket
import time
import unittest
from multiprocessing import Queue
from random import randint

from PiCN.Layers.LinkLayer import UDP4LinkLayer


class TestUDP4LinkLayer(unittest.TestCase):
    """Test the UDP4LinkLayer"""

    def setUp(self):
        self.portoffset = randint(0, 999)  # required for more stable testing if socket is still open for some reason
        self.linklayer1 = UDP4LinkLayer(8000 + self.portoffset, max_fids_entries=int(1e2))
        self.linklayer2 = UDP4LinkLayer(9000 + self.portoffset)
        self.linklayer3 = UDP4LinkLayer(10000 + self.portoffset)

        self.q1_fromHigher = Queue()
        self.q1_toHiger = Queue()
        self.q2_fromHigher = Queue()
        self.q2_toHiger = Queue()
        self.q3_fromHigher = Queue()
        self.q3_toHiger = Queue()

        self.linklayer1.queue_from_higher = self.q1_fromHigher
        self.linklayer1.queue_to_higher = self.q1_toHiger

        self.linklayer2.queue_from_higher = self.q2_fromHigher
        self.linklayer2.queue_to_higher = self.q2_toHiger

        self.linklayer3.queue_from_higher = self.q3_fromHigher
        self.linklayer3.queue_to_higher = self.q3_toHiger

        self.testSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.testSock.bind(("0.0.0.0", 7000 + self.portoffset))


    def tearDown(self):
        self.testSock.close()
        self.linklayer1.stop_process()
        self.linklayer2.stop_process()
        self.linklayer3.stop_process()
        time.sleep(0.7)

    def test_create_new_fid(self):
        """Testing if max number of fid entries is considered"""
        self.linklayer1.start_process()
        for i in range(0,int(1e3)):
            self.linklayer1.create_new_fid(("127.0.0.1", 9000))

        num_of_fids = len(self.linklayer1._fids_to_ip)
        self.assertEqual(num_of_fids, int(1e2)+1)
        num_of_ts = len(self.linklayer1._fids_timestamps)
        self.assertEqual(num_of_ts, int(1e2) + 1)

    def test_create_new_static_fid(self):
        """Testing if static fid entries are correctly considered"""
        self.linklayer1.start_process()
        for i in range(0, int(1e3)):
            self.linklayer1.create_new_fid(("127.0.0.1", 9000), static=True)

        num_of_fids = len(self.linklayer1._fids_to_ip)
        self.assertEqual(num_of_fids, int(1e3))
        num_of_ts = len(self.linklayer1._fids_timestamps)
        self.assertEqual(num_of_ts, 0)

    def test_get_or_create_new_fid(self):
        """Testing if fid entries are correctly found"""
        self.linklayer1.start_process()
        for i in range(0,int(1e3)):
            self.linklayer1.get_or_create_fid(("127.0.0.1", 9000))

        num_of_fids = len(self.linklayer1._fids_to_ip)
        self.assertEqual(num_of_fids, 1)
        num_of_ts = len(self.linklayer1._fids_timestamps)
        self.assertEqual(num_of_ts, 1)

    def test_receiving_a_packet(self):
        """Testing if a packet is received correctly"""
        self.linklayer1.start_process()
        self.testSock.sendto("HelloWorld".encode(), ("127.0.0.1", 8000 + self.portoffset))

        data = self.q1_toHiger.get()
        faceid = data[0]
        content = data[1].decode()
        self.assertEqual(content, "HelloWorld")
        self.assertEqual(self.linklayer1._cur_fid.value, 1)
        self.assertEqual(len(self.linklayer1._fids_timestamps), 1)
        self.assertEqual(len(self.linklayer1._fids_to_ip), 1)
        self.assertEqual(self.linklayer1._fids_to_ip[0], ("127.0.0.1", 7000 + self.portoffset))
        self.assertEqual(len(self.linklayer1._fids_to_ip), 1)

    def test_sending_a_packet(self):
        """Testing if a packet is sent correctly"""
        self.linklayer1.start_process()

        fid = self.linklayer1.create_new_fid(("127.0.0.1", 7000 + self.portoffset))
        self.q1_fromHigher.put([fid, "HelloWorld".encode()])

        data, addr = self.testSock.recvfrom(8192)

        self.assertEqual(data.decode(), "HelloWorld")

    def test_sending_and_receiving_a_packet(self):
        """Testing sending/receiving in a single case"""
        self.linklayer1.start_process()
        self.linklayer2.start_process()

        fid = self.linklayer1.create_new_fid(("127.0.0.1", 9000 + self.portoffset))
        self.q1_fromHigher.put([fid, "HelloWorld".encode()])

        data = self.q2_toHiger.get()
        faceid = data[0]
        packet = data[1]

        self.assertEqual(packet.decode(), "HelloWorld")

    def test_sending_and_receiving_packets(self):
        """Testing sending/receiving many packets in a single case"""
        self.linklayer1.start_process()
        self.linklayer2.start_process()

        fid1 = self.linklayer1.create_new_fid(("127.0.0.1", 9000 + self.portoffset), static=True)
        fid2 = self.linklayer2.create_new_fid(("127.0.0.1", 8000 + self.portoffset), static=True)

        for i in range(1,1000):
            str1 = "HelloWorld" + str(i)
            str2 = "GoodBye" + str(i)
            self.q1_fromHigher.put([fid1, str1.encode()])
            self.q2_fromHigher.put([fid2, str2.encode()])

            d2 = self.q2_toHiger.get()
            d1 = self.q1_toHiger.get()

            # This is correct, packets must be exchanged, since they where sent to the other node
            packet2 = d1[1].decode()
            packet1 = d2[1].decode()

            self.assertEqual(packet1, str1)
            self.assertEqual(packet2, str2)

            self.assertEqual(d1[0], fid1)
            self.assertEqual(d2[0], fid2)

        #Same test, little different order
        for i in range(1, 1000):
            str1 = "HelloWorld" + str(i)
            str2 = "GoodBye" + str(i)

            self.q2_fromHigher.put([fid2, str2.encode()])
            self.q1_fromHigher.put([fid1, str1.encode()])

            d2 = self.q2_toHiger.get()
            d1 = self.q1_toHiger.get()

            # This is correct, packets must be exchanged, since they where sent to the other node
            packet2 = d1[1].decode()
            packet1 = d2[1].decode()

            self.assertEqual(packet1, str1)
            self.assertEqual(packet2, str2)

            self.assertEqual(d1[0], fid1)
            self.assertEqual(d2[0], fid2)

    def test_sending_and_receiving_packets_three_nodes(self):
        """Testing sending/receiving packets with three nodes"""
        self.linklayer1.start_process()
        self.linklayer2.start_process()
        self.linklayer3.start_process()

        fid1_2 = self.linklayer1.create_new_fid(("127.0.0.1", 9000 + self.portoffset), static=True)
        fid1_3 = self.linklayer1.create_new_fid(("127.0.0.1", 10000 + self.portoffset), static=True)

        fid2_1 = self.linklayer2.create_new_fid(("127.0.0.1", 8000 + self.portoffset), static=True)

        fid3_1 = self.linklayer3.create_new_fid(("127.0.0.1", 8000 + self.portoffset), static=True)
        fid3_2 = self.linklayer3.create_new_fid(("127.0.0.1", 9000 + self.portoffset), static=True)

        for i in range(1, 100):
            str1 = "Node1" + str(i)
            str2 = "Node2" + str(i)
            str3 = "Node3" + str(i)

            # Node 1 ---> Node 2
            self.q1_fromHigher.put([fid1_2, str1.encode()])
            data1_2 = self.q2_toHiger.get()
            # Node 1 ---> Node 3
            self.q1_fromHigher.put([fid1_3, str1.encode()])
            data1_3 = self.q3_toHiger.get()
            # Node 2 ---> Node 1
            self.q2_fromHigher.put([fid2_1, str2.encode()])
            data2_1 = self.q1_toHiger.get()
            # Node 3 ---> Node 1
            self.q3_fromHigher.put([fid3_1, str3.encode()])
            data3_1 = self.q1_toHiger.get()
            # Node 3 ---> Node 2
            self.q3_fromHigher.put([fid3_2, str3.encode()])
            data3_2 = self.q2_toHiger.get()

            self.assertEqual(data1_2[1].decode(), str1)
            self.assertEqual(data1_3[1].decode(), str1)
            self.assertEqual(data2_1[1].decode(), str2)
            self.assertEqual(data3_1[1].decode(), str3)
            self.assertEqual(data3_2[1].decode(), str3)
