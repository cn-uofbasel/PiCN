"""Test the BasicPacketEncodingLayer"""

import time
import unittest
from multiprocessing import Queue
from random import randint

from PiCN.Layers.PacketEncodingLayer import BasicPacketEncodingLayer
from PiCN.Layers.PacketEncodingLayer.Encoder import SimpleStringEncoder

from PiCN.Layers.LinkLayer import UDP4LinkLayer
from PiCN.Layers.PacketEncodingLayer.Encoder import BasicEncoder
from PiCN.Packets import Packet, Content, Interest, Nack

class TestBasicPacketEncodingLayer(unittest.TestCase):

    def setUp(self):
        self.portoffset = randint(0,999)
        self.encoder1 = SimpleStringEncoder()
        self.packetEncodingLayer1 = BasicPacketEncodingLayer()
        self.packetEncodingLayer2 = BasicPacketEncodingLayer()

        self.linkLayer1 = UDP4LinkLayer(2000+self.portoffset)
        self.linkLayer2 = UDP4LinkLayer(3000+self.portoffset)
        self.encoder2 = SimpleStringEncoder()

        self.q1_fromLower = Queue()
        self.q1_fromHigher = Queue()
        self.q1_toLower = Queue()
        self.q1_toHigher = Queue()

        self.q2_fromLower = Queue()
        self.q2_fromHigher = Queue()
        self.q2_toLower = Queue()
        self.q2_toHigher = Queue()

        self.packetEncodingLayer1.queue_from_lower = self.q1_fromLower
        self.packetEncodingLayer1.queue_from_higher = self.q1_fromHigher
        self.packetEncodingLayer1.queue_to_lower = self.q1_toLower
        self.packetEncodingLayer1.queue_to_higher = self.q1_toHigher

        self.packetEncodingLayer2.queue_from_lower = self.q2_fromLower
        self.packetEncodingLayer2.queue_from_higher = self.q2_fromHigher
        self.packetEncodingLayer2.queue_to_lower = self.q2_toLower
        self.packetEncodingLayer2.queue_to_higher = self.q2_toHigher

        self.linkLayer1.queue_from_higher = self.q1_toLower #from higher in Linklayer is to Lower from Encoding Layer
        self.linkLayer1.queue_to_higher = self.q1_fromLower #to higher in Linklayer is from lower from Encoding Layer

        self.linkLayer2.queue_from_higher = self.q2_toLower  # from higher in Linklayer is to Lower from Encoding Layer
        self.linkLayer2.queue_to_higher = self.q2_fromLower  # to higher in Linklayer is from lower from Encoding Layer

        self.packetEncodingLayer1.encoder = self.encoder1
        self.packetEncodingLayer2.encoder = self.encoder2

    def tearDown(self):
        self.packetEncodingLayer1.stop_process()
        self.packetEncodingLayer2.stop_process()
        self.linkLayer1.stop_process()
        self.linkLayer2.stop_process()
        time.sleep(0.3)

    def test_EncoderMock_encode_interest_equal(self):
        """Test the interest encoding of EncoderMock: equal"""
        i = Interest("/test/data")
        ei = self.encoder1.encode(i)
        self.assertEqual(ei.decode(), "I:/test/data:")

    def test_EncoderMock_encode_interest_not_equal(self):
        """Test the interest encoding of EncoderMock: not equal"""
        i = Interest("/data/test")
        ei = self.encoder1.encode(i)
        self.assertNotEqual(ei.decode(), "I:/test/data:")

    def test_EncoderMock_decode_interest_equal(self):
        """Test the interest decoding of EncoderMock: equal"""
        data = "I:/test/data:".encode()
        di = self.encoder1.decode(data)
        cmp_interest = Interest("/test/data")
        self.assertTrue(di == cmp_interest)

    def test_EncoderMock_decode_interest_equal(self):
        """Test the interest decoding of EncoderMock: not equal"""
        data = "I:/data/test:".encode()
        di = self.encoder1.decode(data)
        cmp_interest = Interest("/test/data")
        self.assertFalse(di == cmp_interest)

    def test_EncoderMock_encode_decode_interest(self):
        """Test the interest decoding of EncoderMock: equal"""
        i = Interest("/data/test")
        ei = self.encoder1.encode(i)
        di = self.encoder1.decode(ei)
        self.assertTrue(i == di)

    def test_EncoderMock_decode_content_equal(self):
        """Test the Content decoding of EncoderMock: equal"""
        data = "C:/data/test::HelloWorld".encode()
        dc = self.encoder1.decode(data)
        cmp_interest = Content("/data/test", "HelloWorld")
        self.assertTrue(dc == cmp_interest)

    def test_EncoderMock_decode_content_not_equal(self):
        """Test the Content decoding of EncoderMock: not equal"""
        data = "C:/data/test::HelloWorld2".encode()
        dc = self.encoder1.decode(data)
        cmp_interest = Content("/data/test", "HelloWorld")
        self.assertFalse(dc == cmp_interest)

    def test_EncoderMock_encode_decode_content(self):
        """Test the content decoding of EncoderMock"""
        c = Content("/data/test", "HelloWorld")
        ec = self.encoder1.encode(c)
        dc = self.encoder1.decode(ec)
        self.assertTrue(c == dc)

    def test_EncoderMock_encode_decode_nack(self):
        """Test the nack decoding of EncoderMock"""
        n = Nack("/data/test", reason="reason1")
        en = self.encoder1.encode(n)
        dn = self.encoder1.decode(en)
        self.assertTrue(n == dn)

    def test_BasicPacketEncodingLayer_downwards(self):
        """Test the BasicPacketEncodingLayer downwards"""
        self.packetEncodingLayer1.start_process()

        #test interest
        self.q1_fromHigher.put([2, Interest("/test/data")])
        cmp_data = "I:/test/data:".encode()
        data = self.q1_toLower.get()
        self.assertEqual([2, cmp_data], data)

        # test content
        self.q1_fromHigher.put([3, Content("/test/data", "HelloWorld")])
        cmp_data = "C:/test/data::HelloWorld".encode()
        data = self.q1_toLower.get()
        self.assertEqual([3, cmp_data], data)


    def test_BasicPacketEncodingLayer_upwards(self):
        """Test the BasicPacketEncodingLayer upwards"""
        self.packetEncodingLayer1.start_process()

        #test interest
        data = [2, "I:/test/data:".encode()]
        cmp_i = [2, Interest("/test/data")]
        self.q1_fromLower.put(data)
        i = self.q1_toHigher.get()
        self.assertEqual(i, cmp_i)

        #test content
        data = [2, "C:/test/data::HelloWorld".encode()]
        cmp_i = [2, Content("/test/data", "HelloWorld")]
        self.q1_fromLower.put(data)
        i = self.q1_toHigher.get()
        self.assertEqual(i, cmp_i)


    def test_BasicPacketEncodingLayer_bidirectional(self):
        """Test the BasicPacketEncodingLayer bidirectional"""
        self.packetEncodingLayer1.start_process()

        #test interest
        i = [2, Interest("/test/data")]
        self.q1_fromHigher.put(i)
        ei = self.q1_toLower.get()
        self.q1_fromLower.put(ei)
        di = self.q1_toHigher.get()
        self.assertEqual(i, di)

        #test content
        c = [2, Content("/test/data", "HelloWorld")]
        self.q1_fromHigher.put(c)
        ec = self.q1_toLower.get()
        self.q1_fromLower.put(ec)
        dc = self.q1_toHigher.get()
        self.assertEqual(c, dc)

    def test_BasicPacketEncodingLayer_interest_transfer_udp4(self):
        """Test the BasicPacketEncodingLayer and the UDP4LinkLayer to verify interest transport"""
        self.linkLayer1.start_process()
        self.linkLayer2.start_process()
        self.packetEncodingLayer1.start_process()
        self.packetEncodingLayer2.start_process()
        fid = self.linkLayer1.create_new_fid(("127.0.0.1", 3000+self.portoffset))
        i = Interest("/test/data")

        #PUT interest in node 1 queues
        self.packetEncodingLayer1.queue_from_higher.put([fid, i])
        #GET interest from node 2 queues
        data = self.packetEncodingLayer2.queue_to_higher.get()

        #Check Packet
        ri = data[1]
        self.assertEqual(ri, i)

    def test_BasicPacketEncodingLayer_content_transfer_udp4(self):
        """Test the BasicPacketEncodingLayer and the UDP4LinkLayer to verify content transport"""
        self.linkLayer1.start_process()
        self.linkLayer2.start_process()
        self.packetEncodingLayer1.start_process()
        self.packetEncodingLayer2.start_process()
        fid = self.linkLayer1.create_new_fid(("127.0.0.1", 3000 + self.portoffset))
        c = Content("/test/data", "HelloWorld")

        # PUT interest in node 1 queues
        self.packetEncodingLayer1.queue_from_higher.put([fid, c])
        # GET interest from node 2 queues
        data = self.packetEncodingLayer2.queue_to_higher.get()

        # Check Packet
        rc = data[1]
        self.assertEqual(rc, c)




