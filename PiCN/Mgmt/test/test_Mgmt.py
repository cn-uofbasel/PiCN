"""Tests for the Mgmt Interface"""

import multiprocessing
import socket
import time
import unittest
from random import randint

from PiCN.Layers.ICNLayer.ForwardingInformationBase import ForwardingInformationBaseMemoryPrefix
from PiCN.Layers.ICNLayer.PendingInterestTable import PendingInterstTableMemoryExact

from PiCN.Layers.ICNLayer.ContentStore import ContentStoreMemoryExact
from PiCN.Layers.LinkLayer import UDP4LinkLayer
from PiCN.Mgmt import Mgmt
from PiCN.Mgmt import MgmtClient
from PiCN.Packets import Name


class test_Mgmt(unittest.TestCase):

    def setUp(self):
        self.manager = multiprocessing.Manager()
        self.linklayer = UDP4LinkLayer(0)
        self.linklayerport = self.linklayer.get_port()
        self.q1 = multiprocessing.Queue()
        self.linklayer.queue_from_higher = self.q1

        self._data_structs = self.manager.dict()
        self._data_structs['cs'] = ContentStoreMemoryExact()
        self._data_structs['fib'] = ForwardingInformationBaseMemoryPrefix()
        self._data_structs['pit'] = PendingInterstTableMemoryExact()

        self.mgmt = Mgmt(self._data_structs, self.linklayer, self.linklayerport)
        self.testMgmtSock1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.testMgmtSock2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.testMgmtSock3 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.mgmt_client = MgmtClient(self.linklayerport)


    def tearDown(self):
        self.linklayer.stop_process()
        self.mgmt.stop_process()
        self.testMgmtSock1.close()
        self.testMgmtSock2.close()
        self.testMgmtSock3.close()

    def test_mgmt_new_face(self):
        """Test the mgmt interace to create a new face"""
        self.linklayer.start_process()
        self.mgmt.start_process()

        self.testMgmtSock1.connect(("127.0.0.1", self.linklayerport))
        self.testMgmtSock1.send("GET /linklayer/newface/127.0.0.1:9000 HTTP/1.1\r\n\r\n".encode())
        data = self.testMgmtSock1.recv(1024)
        self.testMgmtSock1.close()

        self.assertEqual(data.decode(),
                         "HTTP/1.1 200 OK \r\n Content-Type: text/html \r\n\r\n newface OK:0\r\n")

        self.assertEqual(len(self.linklayer._ip_to_fid), 1)
        self.assertEqual(len(self.linklayer._fids_to_ip), 1)
        self.assertEqual(self.linklayer._ip_to_fid[("127.0.0.1", 9000)], 0)
        self.assertEqual(self.linklayer._fids_to_ip[0], ("127.0.0.1", 9000))


    def test_mgmt_multiple_new_face(self):
        """Test the mgmt interace to create multiple new faces with deduplication"""
        self.linklayer.start_process()
        self.mgmt.start_process()

        self.testMgmtSock1.connect(("127.0.0.1", self.linklayerport))
        self.testMgmtSock1.send("GET /linklayer/newface/127.0.0.1:9000 HTTP/1.1\r\n\r\n".encode())
        data = self.testMgmtSock1.recv(1024)
        self.testMgmtSock1.close()

        self.assertEqual(data.decode(),
                         "HTTP/1.1 200 OK \r\n Content-Type: text/html \r\n\r\n newface OK:0\r\n")

        self.testMgmtSock2.connect(("127.0.0.1",self.linklayerport))
        self.testMgmtSock2.send("GET /linklayer/newface/127.0.0.1:8000 HTTP/1.1\r\n\r\n".encode())
        data = self.testMgmtSock2.recv(1024)
        self.testMgmtSock2.close()


        self.assertEqual(data.decode(),
                         "HTTP/1.1 200 OK \r\n Content-Type: text/html \r\n\r\n newface OK:1\r\n")

        self.testMgmtSock3.connect(("127.0.0.1", self.linklayerport))
        self.testMgmtSock3.send("GET /linklayer/newface/127.0.0.1:9000 HTTP/1.1\r\n\r\n".encode())
        data = self.testMgmtSock3.recv(1024)
        self.testMgmtSock3.close()


        self.assertEqual(data.decode(),
                         "HTTP/1.1 200 OK \r\n Content-Type: text/html \r\n\r\n newface OK:0\r\n")

        self.assertEqual(len(self.linklayer._ip_to_fid), 2)
        self.assertEqual(len(self.linklayer._fids_to_ip), 2)
        self.assertEqual(self.linklayer._ip_to_fid[("127.0.0.1", 9000)], 0)
        self.assertEqual(self.linklayer._fids_to_ip[0], ("127.0.0.1", 9000))
        self.assertEqual(self.linklayer._ip_to_fid[("127.0.0.1", 8000)], 1)
        self.assertEqual(self.linklayer._fids_to_ip[1], ("127.0.0.1", 8000))

    def test_mgmt_add_forwaring_rule(self):
        """Test adding Forwarding rules"""
        self.linklayer.start_process()
        self.mgmt.start_process()

        self.testMgmtSock1.connect(("127.0.0.1", self.linklayerport))
        self.testMgmtSock1.send("GET /icnlayer/newforwardingrule/%2Ftest%2Fdata:2 HTTP/1.1\r\n\r\n".encode())
        data = self.testMgmtSock1.recv(1024)
        self.testMgmtSock1.close()
        self.assertEqual(data.decode(),
                         "HTTP/1.1 200 OK \r\n Content-Type: text/html \r\n\r\n newforwardingrule OK:2\r\n")

        time.sleep(1)

        self.testMgmtSock2.connect(("127.0.0.1", self.linklayerport))
        self.testMgmtSock2.send("GET /icnlayer/newforwardingrule/%2Fdata%2Ftest:3 HTTP/1.1\r\n\r\n".encode())
        data = self.testMgmtSock2.recv(1024)
        self.testMgmtSock2.close()

        self.assertEqual(data.decode(),
                         "HTTP/1.1 200 OK \r\n Content-Type: text/html \r\n\r\n newforwardingrule OK:3\r\n")

        self.assertEqual(self._data_structs.get('fib').find_fib_entry(Name("/test/data")).faceid, 2)
        self.assertEqual(self._data_structs.get('fib').find_fib_entry(Name("/data/test")).faceid, 3)

    def test_mgmt_add_content(self):
        """Test adding content"""
        self.linklayer.start_process()
        self.mgmt.start_process()

        self.testMgmtSock1.connect(("127.0.0.1", self.linklayerport))
        self.testMgmtSock1.send("GET /icnlayer/newcontent/%2Ftest%2Fdata:HelloWorld HTTP/1.1\r\n\r\n".encode())
        data = self.testMgmtSock1.recv(1024)
        self.testMgmtSock1.close()
        self.assertEqual(data.decode(),
                         "HTTP/1.1 200 OK \r\n Content-Type: text/html \r\n\r\n newcontent OK\r\n")

        time.sleep(1)

        self.testMgmtSock2.connect(("127.0.0.1", self.linklayerport))
        self.testMgmtSock2.send("GET /icnlayer/newcontent/%2Fdata%2Ftest:GoodBye HTTP/1.1\r\n\r\n".encode())
        data = self.testMgmtSock2.recv(1024)
        self.testMgmtSock2.close()

        self.assertEqual(data.decode(),
                         "HTTP/1.1 200 OK \r\n Content-Type: text/html \r\n\r\n newcontent OK\r\n")

        cs = self._data_structs.get('cs')
        self.assertEqual(cs.find_content_object(Name("/test/data")).content.content, "HelloWorld")
        self.assertEqual(cs.find_content_object(Name("/data/test")).content.content, "GoodBye")


    def test_add_face_mgmt_client(self):
        """Test adding a face using the mgmtclient"""
        self.linklayer.start_process()
        self.mgmt.start_process()
        data = self.mgmt_client.add_face("127.0.0.1", 9000)
        self.assertEqual(data, "HTTP/1.1 200 OK \r\n Content-Type: text/html \r\n\r\n newface OK:0\r\n")
        self.assertEqual(len(self.linklayer._ip_to_fid), 1)
        self.assertEqual(len(self.linklayer._fids_to_ip), 1)
        self.assertEqual(self.linklayer._ip_to_fid[("127.0.0.1", 9000)], 0)
        self.assertEqual(self.linklayer._fids_to_ip[0], ("127.0.0.1", 9000))

    def test_add_forwarding_rule_mgmt_client(self):
        """Test adding forwarding rule using MgmtClient"""
        self.linklayer.start_process()
        self.mgmt.start_process()

        data = self.mgmt_client.add_forwarding_rule(Name("/test/data"), 2)
        self.assertEqual("HTTP/1.1 200 OK \r\n Content-Type: text/html \r\n\r\n newforwardingrule OK:2\r\n", data)

        time.sleep(1)
        data = self.mgmt_client.add_forwarding_rule(Name("/data/test"), 3)
        self.assertEqual(data, "HTTP/1.1 200 OK \r\n Content-Type: text/html \r\n\r\n newforwardingrule OK:3\r\n")

        self.assertEqual(self._data_structs.get('fib').find_fib_entry(Name("/test/data")).faceid, 2)
        self.assertEqual(self._data_structs.get('fib').find_fib_entry(Name("/data/test")).faceid, 3)

    def test_mgmt_add_content_mgmt_client(self):
        """Test adding content using MgmtClient"""
        self.linklayer.start_process()
        self.mgmt.start_process()

        data = self.mgmt_client.add_new_content(Name("/test/data"), "HelloWorld")
        self.assertEqual(data, "HTTP/1.1 200 OK \r\n Content-Type: text/html \r\n\r\n newcontent OK\r\n")

        time.sleep(1)
        data = self.mgmt_client.add_new_content(Name("/data/test"), "GoodBye")
        self.assertEqual(data, "HTTP/1.1 200 OK \r\n Content-Type: text/html \r\n\r\n newcontent OK\r\n")

        cs = self._data_structs.get('cs')
        self.assertEqual(cs.find_content_object(Name("/test/data")).content.content, "HelloWorld")
        self.assertEqual(cs.find_content_object(Name("/data/test")).content.content, "GoodBye")

    def test_mgmt_shutdown_mgmt_client(self):
        """Test adding content"""
        self.linklayer.start_process()
        self.mgmt.start_process()
        data = self.mgmt_client.shutdown()
        self.assertEqual(data, "HTTP/1.1 200 OK \r\n Content-Type: text/html \r\n\r\n shutdown\r\n")