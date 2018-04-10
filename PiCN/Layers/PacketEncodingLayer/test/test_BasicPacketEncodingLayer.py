"""Test the BasicPacketEncodingLayer"""


import abc
import unittest

from multiprocessing import Queue


from PiCN.Layers.PacketEncodingLayer import BasicPacketEncodingLayer
from PiCN.Layers.PacketEncodingLayer.Encoder import SimpleStringEncoder, NdnTlvEncoder

from PiCN.Layers.LinkLayer import UDP4LinkLayer
from PiCN.Layers.PacketEncodingLayer.Encoder import BasicEncoder
from PiCN.Packets import Packet, Content, Interest, Nack, NackReason

class cases_BasicPacketEncodingLayer(object):

    @abc.abstractmethod
    def get_encoder(self):
        """returns the encoder to be used"""

    def setUp(self):
        self.encoder1 = self.get_encoder()
        self.encoder2 = self.get_encoder()
        self.packetEncodingLayer1 = BasicPacketEncodingLayer(encoder=self.encoder1)
        self.packetEncodingLayer2 = BasicPacketEncodingLayer(encoder=self.encoder2)

        self.linkLayer1 = UDP4LinkLayer(0)
        self.linkLayer2 = UDP4LinkLayer(0)
        self.port1 = self.linkLayer1.get_port()
        self.port2 = self.linkLayer2.get_port()


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


    def tearDown(self):
        self.packetEncodingLayer1.stop_process()
        self.packetEncodingLayer2.stop_process()
        self.linkLayer1.stop_process()
        self.linkLayer2.stop_process()

    def test_BasicPacketEncodingLayer_bidirectional(self):
        """Test the BasicPacketEncodingLayer bidirectional"""
        self.packetEncodingLayer1.start_process()

        #test interest
        i = [2, Interest("/test/data")]
        self.q1_fromHigher.put(i)
        try:
            ei = self.q1_toLower.get(timeout=2.0)
        except:
            self.fail()
        self.q1_fromLower.put(ei)
        di = self.q1_toHigher.get()
        self.assertEqual(i, di)

        #test content
        c = [2, Content("/test/data", "HelloWorld")]
        self.q1_fromHigher.put(c)
        try:
            ec = self.q1_toLower.get(timeout=2.0)
        except:
            self.fail()
        self.q1_fromLower.put(ec)
        try:
            dc = self.q1_toHigher.get(timeout=2.0)
        except:
            self.fail()
        self.assertEqual(c, dc)

    def test_BasicPacketEncodingLayer_interest_transfer_udp4(self):
        """Test the BasicPacketEncodingLayer and the UDP4LinkLayer to verify interest transport"""
        self.linkLayer1.start_process()
        self.linkLayer2.start_process()
        self.packetEncodingLayer1.start_process()
        self.packetEncodingLayer2.start_process()
        fid = self.linkLayer1.create_new_fid(("127.0.0.1", self.port2))
        i = Interest("/test/data")

        #PUT interest in node 1 queues
        self.packetEncodingLayer1.queue_from_higher.put([fid, i])
        #GET interest from node 2 queues
        try:
            data = self.packetEncodingLayer2.queue_to_higher.get(timeout=2.0)
        except:
            self.fail()

        #Check Packet
        ri = data[1]
        self.assertEqual(ri, i)

    def test_BasicPacketEncodingLayer_content_transfer_udp4(self):
        """Test the BasicPacketEncodingLayer and the UDP4LinkLayer to verify content transport"""
        self.linkLayer1.start_process()
        self.linkLayer2.start_process()
        self.packetEncodingLayer1.start_process()
        self.packetEncodingLayer2.start_process()
        fid = self.linkLayer1.create_new_fid(("127.0.0.1", self.port2))
        c = Content("/test/data", "HelloWorld")

        # PUT interest in node 1 queues
        self.packetEncodingLayer1.queue_from_higher.put([fid, c])
        # GET interest from node 2 queues
        try:
            data = self.packetEncodingLayer2.queue_to_higher.get(timeout=2.0)
        except:
            self.fail()

        # Check Packet
        rc = data[1]
        self.assertEqual(rc, c)


class test_BasicPacketEncodingLayer_SimplePacketEncoder(cases_BasicPacketEncodingLayer, unittest.TestCase):
    """Runs tests with the SimplePacketEncoder"""
    def get_encoder(self):
        return SimpleStringEncoder()

class test_BasicPacketEncodingLayer_NDNTLVPacketEncoder(cases_BasicPacketEncodingLayer, unittest.TestCase):
    """Runs tests with the NDNTLVPacketEncoder"""
    def get_encoder(self):
        return NdnTlvEncoder()
