"""Test the ICN Forwarder"""

import abc
import socket
import time
import unittest

from PiCN.Layers.PacketEncodingLayer.Encoder import SimpleStringEncoder, NdnTlvEncoder
from PiCN.Packets import Content, Interest, Name
from PiCN.ProgramLibs.ICNForwarder import ICNForwarder
from PiCN.Layers.LinkLayer.Interfaces import AddressInfo

class cases_ICNForwarder(object):
    """Test the ICN Forwarder"""

    @abc.abstractmethod
    def get_encoder(self):
        """returns the encoder to be used """

    def setUp(self):
        self.encoder = self.get_encoder()
        self.forwarder1 = ICNForwarder(0, encoder=self.get_encoder(), log_level=255)
        self.forwarder2 = ICNForwarder(0, encoder=self.get_encoder(), log_level=255)
        self.forwarder1_port = self.forwarder1.linklayer.interfaces[0].get_port()
        self.forwarder2_port = self.forwarder2.linklayer.interfaces[0].get_port()

        self.testSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.testSock.bind(("0.0.0.0", 0))

    def tearDown(self):
        self.forwarder1.stop_forwarder()
        self.forwarder2.stop_forwarder()
        self.testSock.close()
        pass


    def test_ICNForwarder_simple_find_content_one_node(self):
        """Test a simple forwarding scenario, getting content from a Node"""
        self.forwarder1.start_forwarder()

        # new content
        testMgmtSock1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        testMgmtSock1.connect(("127.0.0.1", self.forwarder1_port))
        testMgmtSock1.send("GET /icnlayer/newcontent/%2Ftest%2Fdata%2Fobject:HelloWorld HTTP/1.1\r\n\r\n".encode())
        data = testMgmtSock1.recv(1024)
        testMgmtSock1.close()
        time.sleep(3)

        self.assertEqual(data.decode(),
                         "HTTP/1.1 200 OK \r\n Content-Type: text/html \r\n\r\n newcontent OK\r\n")

        #create test content
        name = Name("/test/data/object")
        test_content = Content(name, content="HelloWorld")
        cs_fwd1 = self.forwarder1.icnlayer.cs
        self.assertEqual(cs_fwd1.find_content_object(name).content, test_content)

        #create interest
        interest = Interest("/test/data/object")
        encoded_interest = self.encoder.encode(interest)
        #send interest
        self.testSock.sendto(encoded_interest, ("127.0.0.1", self.forwarder1_port))
        #receive content
        encoded_content, addr = self.testSock.recvfrom(8192)
        content = self.encoder.decode(encoded_content)
        self.assertEqual(content, test_content)

    def test_ICNForwarder_simple_find_content_two_nodes(self):
        """Test a simple forwarding scenario with one additional node forwarding the data"""
        self.forwarder1.start_forwarder()
        self.forwarder2.start_forwarder()
        #client <---> node1 <---> node2

        #create a face
        testMgmtSock1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        testMgmtSock1.connect(("127.0.0.1", self.forwarder1_port))
        port_to = self.forwarder2_port
        testMgmtSock1.send(("GET /linklayer/newface/127.0.0.1:" + str(port_to) + ":0 HTTP/1.1\r\n\r\n").encode())
        data = testMgmtSock1.recv(1024)
        testMgmtSock1.close()
        self.assertEqual(data.decode(),
                         "HTTP/1.1 200 OK \r\n Content-Type: text/html \r\n\r\n newface OK:0\r\n")
        self.assertEqual(self.forwarder1.linklayer.faceidtable.get_face_id(AddressInfo(("127.0.0.1", self.forwarder2_port), 0)), 0)

        #register a prefix
        testMgmtSock2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        testMgmtSock2.connect(("127.0.0.1", self.forwarder1_port))
        testMgmtSock2.send("GET /icnlayer/newforwardingrule/%2Ftest%2Fdata:0 HTTP/1.1\r\n\r\n".encode())
        data = testMgmtSock2.recv(1024)
        testMgmtSock2.close()
        self.assertEqual(data.decode(),
                         "HTTP/1.1 200 OK \r\n Content-Type: text/html \r\n\r\n newforwardingrule OK:0\r\n")
        self.assertEqual(self.forwarder1.icnlayer.fib.find_fib_entry(Name("/test/data")).faceid, 0)

        # new content
        testMgmtSock3 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        testMgmtSock3.connect(("127.0.0.1", self.forwarder2_port))
        testMgmtSock3.send("GET /icnlayer/newcontent/%2Ftest%2Fdata%2Fobject:HelloWorld HTTP/1.1\r\n\r\n".encode())
        data = testMgmtSock3.recv(1024)
        testMgmtSock3.close()
        self.assertEqual(data.decode(),
                         "HTTP/1.1 200 OK \r\n Content-Type: text/html \r\n\r\n newcontent OK\r\n")

        #create test content
        name = Name("/test/data/object")
        test_content = Content(name, content="HelloWorld")
        cs_fwd2 = self.forwarder2.icnlayer.cs
        self.assertEqual(cs_fwd2.find_content_object(name).content, test_content)

        #create interest
        interest = Interest("/test/data/object")
        encoded_interest = self.encoder.encode(interest)
        #send interest
        self.testSock.sendto(encoded_interest, ("127.0.0.1", self.forwarder1_port))

        #receive content
        encoded_content, addr = self.testSock.recvfrom(8192)
        content = self.encoder.decode(encoded_content)
        self.assertEqual(content, test_content)
        time.sleep(2)
        self.assertEqual(self.forwarder1.icnlayer.pit.get_container_size(), 0)



class test_ICNForwarder_SimplePacketEncoder(cases_ICNForwarder, unittest.TestCase):
    """Runs tests with the SimplePacketEncoder"""
    def get_encoder(self):
        return SimpleStringEncoder()

class test_ICNForwarder_NDNTLVPacketEncoder(cases_ICNForwarder, unittest.TestCase):
    """Runs tests with the NDNTLVPacketEncoder"""
    def get_encoder(self):
        return NdnTlvEncoder()