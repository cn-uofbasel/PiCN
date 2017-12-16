"""Test the ICN Forwarder"""

import socket
import time
import unittest
from random import randint

from PiCN.Layers.PacketEncodingLayer.Encoder import SimpleStringEncoder
from PiCN.Packets import Content, Interest, Name
from PiCN.ProgramLibs.NFNForwarder import NFNForwarder
from PiCN.Layers.NFNLayer.NFNEvaluator.NFNExecutor import NFNPythonExecutor

class test_NFNForwarder(unittest.TestCase):
    """Test the ICN Forwarder"""

    def setUp(self):
        self.portoffset = randint(0,999)

        self.forwarder1 = NFNForwarder(3000 + self.portoffset, debug_level=255)
        self.forwarder2 = NFNForwarder(4000 + self.portoffset, debug_level=255)
        self.encoder = SimpleStringEncoder()

        self.testSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.testSock.bind(("0.0.0.0", 2000 + self.portoffset))

    def tearDown(self):
        self.forwarder1.stop_forwarder()
        self.forwarder2.stop_forwarder()
        self.testSock.close()
        pass

    def test_NFNForwarder_simple_find_content_one_node(self):
        """Test a simple forwarding scenario, getting content from a Node"""
        self.forwarder1.start_forwarder()

        # new content
        testMgmtSock1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        testMgmtSock1.connect(("127.0.0.1", 3000 + self.portoffset))
        testMgmtSock1.send("GET /icnlayer/newcontent/%2Ftest%2Fdata%2Fobject:HelloWorld HTTP/1.1\r\n\r\n".encode())
        data = testMgmtSock1.recv(1024)
        testMgmtSock1.close()
        time.sleep(3)

        self.assertEqual(data.decode(),
                         "HTTP/1.1 200 OK \r\n Content-Type: text/html \r\n\r\n newcontent OK\r\n")

        #create test content
        name = Name("/test/data/object")
        test_content = Content(name, content="HelloWorld")
        self.assertEqual(self.forwarder1.cs.find_content_object(name).content, test_content)

        #create interest
        interest = Interest("/test/data/object")
        encoded_interest = self.encoder.encode(interest)
        #send interest
        self.testSock.sendto(encoded_interest, ("127.0.0.1", 3000 + self.portoffset))
        #receive content
        encoded_content, addr = self.testSock.recvfrom(8192)
        content = self.encoder.decode(encoded_content)
        self.assertEqual(content, test_content)

    def test_NFNForwarder_simple_find_content_two_nodes(self):
        """Test a simple forwarding scenario with one additional node forwarding the data"""
        self.forwarder1.start_forwarder()
        self.forwarder2.start_forwarder()
        #client <---> node1 <---> node2

        #create a face
        testMgmtSock1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        testMgmtSock1.connect(("127.0.0.1", 3000 + self.portoffset))
        port_to = 4000 + self.portoffset
        testMgmtSock1.send(("GET /linklayer/newface/127.0.0.1:" + str(port_to) + " HTTP/1.1\r\n\r\n").encode())
        data = testMgmtSock1.recv(1024)
        testMgmtSock1.close()
        self.assertEqual(data.decode(),
                         "HTTP/1.1 200 OK \r\n Content-Type: text/html \r\n\r\n newface OK:0\r\n")
        self.assertEqual(self.forwarder1.linklayer._ip_to_fid[("127.0.0.1", 4000 + self.portoffset)], 0)

        #register a prefix
        testMgmtSock2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        testMgmtSock2.connect(("127.0.0.1", 3000 + self.portoffset))
        testMgmtSock2.send("GET /icnlayer/newforwardingrule/%2Ftest%2Fdata:0 HTTP/1.1\r\n\r\n".encode())
        data = testMgmtSock2.recv(1024)
        testMgmtSock2.close()
        self.assertEqual(data.decode(),
                         "HTTP/1.1 200 OK \r\n Content-Type: text/html \r\n\r\n newforwardingrule OK:0\r\n")
        self.assertEqual(self.forwarder1.fib.find_fib_entry(Name("/test/data")).faceid, 0)

        # new content
        testMgmtSock3 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        testMgmtSock3.connect(("127.0.0.1", 4000 + self.portoffset))
        testMgmtSock3.send("GET /icnlayer/newcontent/%2Ftest%2Fdata%2Fobject:HelloWorld HTTP/1.1\r\n\r\n".encode())
        data = testMgmtSock3.recv(1024)
        testMgmtSock3.close()
        self.assertEqual(data.decode(),
                         "HTTP/1.1 200 OK \r\n Content-Type: text/html \r\n\r\n newcontent OK\r\n")

        #create test content
        name = Name("/test/data/object")
        test_content = Content(name, content="HelloWorld")
        self.assertEqual(self.forwarder2.cs.find_content_object(name).content, test_content)

        #create interest
        interest = Interest("/test/data/object")
        encoded_interest = self.encoder.encode(interest)
        #send interest
        self.testSock.sendto(encoded_interest, ("127.0.0.1", 3000 + self.portoffset))

        #receive content
        encoded_content, addr = self.testSock.recvfrom(8192)
        content = self.encoder.decode(encoded_content)
        self.assertEqual(content, test_content)
        self.assertEqual(len(self.forwarder1.pit.container), 0)
        time.sleep(0.5)

    def test_NFNForwarder_simple_compute_two_nodes(self):
        """Test a simple forwarding scenario with one additional node forwarding the data"""
        self.forwarder1.start_forwarder()
        self.forwarder2.start_forwarder()
        # client <---> node1 <---> node2

        # create a face
        testMgmtSock1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        testMgmtSock1.connect(("127.0.0.1", 3000 + self.portoffset))
        port_to = 4000 + self.portoffset
        testMgmtSock1.send(("GET /linklayer/newface/127.0.0.1:" + str(port_to) + " HTTP/1.1\r\n\r\n").encode())
        data = testMgmtSock1.recv(1024)
        testMgmtSock1.close()
        self.assertEqual(data.decode(),
                         "HTTP/1.1 200 OK \r\n Content-Type: text/html \r\n\r\n newface OK:0\r\n")
        self.assertEqual(self.forwarder1.linklayer._ip_to_fid[("127.0.0.1", 4000 + self.portoffset)], 0)

        # register a prefix
        testMgmtSock2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        testMgmtSock2.connect(("127.0.0.1", 3000 + self.portoffset))
        testMgmtSock2.send("GET /icnlayer/newforwardingrule/%2Flib%2Ffunc:0 HTTP/1.1\r\n\r\n".encode())
        data = testMgmtSock2.recv(1024)
        testMgmtSock2.close()
        self.assertEqual(data.decode(),
                         "HTTP/1.1 200 OK \r\n Content-Type: text/html \r\n\r\n newforwardingrule OK:0\r\n")
        self.assertEqual(0, self.forwarder1.fib.find_fib_entry(Name("/lib/func")).faceid)

        #add function
        testMgmtSock3 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        testMgmtSock3.connect(("127.0.0.1", 4000 + self.portoffset))
        testMgmtSock3.send("GET /icnlayer/newcontent/%2Flib%2Ffunc%2Ff1:PYTHON\nf\ndef f():\n    return 'Hello World' HTTP/1.1\r\n\r\n".encode())
        data = testMgmtSock3.recv(1024)
        testMgmtSock3.close()
        self.assertEqual(data.decode(),
                         "HTTP/1.1 200 OK \r\n Content-Type: text/html \r\n\r\n newcontent OK\r\n")

        # create interest
        name = Name("/lib/func/f1")
        name.components.append("_()")
        name.components.append("NFN")
        encoded_interest = self.encoder.encode(Interest(name))
        # send interest
        self.testSock.sendto(encoded_interest, ("127.0.0.1", 3000 + self.portoffset))
        # receive content
        encoded_content, addr = self.testSock.recvfrom(8192)
        content: Content = self.encoder.decode(encoded_content)
        self.assertEqual("Hello World", content.content)
        self.assertEqual(name, content.name)
        self.assertEqual(len(self.forwarder1.pit.container), 0)
        time.sleep(0.5)

    def test_NFNForwarder_compute_param_two_nodes(self):
        """Test a simple forwarding scenario with one additional node forwarding the data"""
        self.forwarder1.start_forwarder()
        self.forwarder2.start_forwarder()
        # client <---> node1 <---> node2

        # create faces
        fid1 = self.forwarder1.linklayer.get_or_create_fid(("127.0.0.1", 4000 + self.portoffset), True)
        fid2 = self.forwarder2.linklayer.get_or_create_fid(("127.0.0.1", 3000 + self.portoffset), True)

        # register prefixes
        self.forwarder1.fib.add_fib_entry(Name("/lib/func"), fid1, True)
        self.forwarder2.fib.add_fib_entry(Name("/test"), fid2, True)

        # add function
        testMgmtSock5 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        testMgmtSock5.connect(("127.0.0.1", 4000 + self.portoffset))
        testMgmtSock5.send(
            "GET /icnlayer/newcontent/%2Flib%2Ffunc%2Ff1:PYTHON\nf\ndef f(a):\n    return a.upper() HTTP/1.1\r\n\r\n".encode())
        data = testMgmtSock5.recv(1024)
        testMgmtSock5.close()
        self.assertEqual(data.decode(),
                         "HTTP/1.1 200 OK \r\n Content-Type: text/html \r\n\r\n newcontent OK\r\n")

        # add content
        testMgmtSock6 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        testMgmtSock6.connect(("127.0.0.1", 3000 + self.portoffset))
        testMgmtSock6.send("GET /icnlayer/newcontent/%2Ftest%2Fdata%2Fobject:HelloWorld HTTP/1.1\r\n\r\n".encode())
        data = testMgmtSock6.recv(1024)
        testMgmtSock6.close()
        self.assertEqual(data.decode(),
                         "HTTP/1.1 200 OK \r\n Content-Type: text/html \r\n\r\n newcontent OK\r\n")

        # create interest
        name = Name("/lib/func/f1")
        name.components.append("_(/test/data/object)")
        name.components.append("NFN")
        encoded_interest = self.encoder.encode(Interest(name))
        # send interest
        self.testSock.sendto(encoded_interest, ("127.0.0.1", 4000 + self.portoffset))
        # receive content
        encoded_content, addr = self.testSock.recvfrom(8192)
        content: Content = self.encoder.decode(encoded_content)
        self.assertEqual("HELLOWORLD", content.content)
        self.assertEqual(name, content.name)
        self.assertEqual(len(self.forwarder1.pit.container), 0)
        time.sleep(0.5)
        #TODO, name components must be escaped when encoding and unescaped when decoding


