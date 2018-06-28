"""Tests for the Mgmt Interface"""

import multiprocessing
import socket
import time
import unittest
from random import randint

from PiCN.Layers.ICNLayer.ForwardingInformationBase import ForwardingInformationBaseMemoryPrefix
from PiCN.Layers.ICNLayer.PendingInterestTable import PendingInterstTableMemoryExact
from PiCN.Layers.ICNLayer.ContentStore import ContentStoreMemoryExact
from PiCN.Layers.LinkLayer import BasicLinkLayer
from PiCN.Layers.LinkLayer.FaceIDTable import FaceIDDict
from PiCN.Layers.LinkLayer.Interfaces import UDP4Interface, AddressInfo
from PiCN.Mgmt import Mgmt
from PiCN.Mgmt import MgmtClient
from PiCN.Packets import Name
from PiCN.Processes import PiCNSyncDataStructFactory


class test_Mgmt(unittest.TestCase):

    def setUp(self):



        synced_data_struct_factory = PiCNSyncDataStructFactory()
        synced_data_struct_factory.register("cs", ContentStoreMemoryExact)
        synced_data_struct_factory.register("fib", ForwardingInformationBaseMemoryPrefix)
        synced_data_struct_factory.register("pit", PendingInterstTableMemoryExact)
        synced_data_struct_factory.register("faceidtable", FaceIDDict)
        synced_data_struct_factory.create_manager()

        cs = synced_data_struct_factory.manager.cs()
        fib = synced_data_struct_factory.manager.fib()
        pit = synced_data_struct_factory.manager.pit()
        faceidtable = synced_data_struct_factory.manager.faceidtable()

        interface = UDP4Interface(0)

        self.linklayer = BasicLinkLayer(interface, faceidtable)
        self.linklayerport = self.linklayer.interfaces[0].get_port()
        self.q1 = multiprocessing.Queue()
        self.linklayer.queue_from_higher = self.q1

        self.mgmt = Mgmt(cs, fib, pit, self.linklayer, self.linklayerport)
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
        self.testMgmtSock1.send("GET /linklayer/newface/127.0.0.1:9000:0 HTTP/1.1\r\n\r\n".encode())
        data = self.testMgmtSock1.recv(1024)
        self.testMgmtSock1.close()

        self.assertEqual(data.decode(),
                         "HTTP/1.1 200 OK \r\n Content-Type: text/html \r\n\r\n newface OK:0\r\n")

        self.assertEqual(self.linklayer.faceidtable.get_num_entries(), 1)
        self.assertEqual(self.linklayer.faceidtable.get_face_id(AddressInfo(("127.0.0.1", 9000), 0)), 0)
        self.assertEqual(self.linklayer.faceidtable.get_address_info(0), AddressInfo(("127.0.0.1", 9000), 0))


    def test_mgmt_multiple_new_face(self):
        """Test the mgmt interace to create multiple new faces with deduplication"""
        self.linklayer.start_process()
        self.mgmt.start_process()

        self.testMgmtSock1.connect(("127.0.0.1", self.linklayerport))
        self.testMgmtSock1.send("GET /linklayer/newface/127.0.0.1:9000:0 HTTP/1.1\r\n\r\n".encode())
        data = self.testMgmtSock1.recv(1024)
        self.testMgmtSock1.close()

        self.assertEqual(data.decode(),
                         "HTTP/1.1 200 OK \r\n Content-Type: text/html \r\n\r\n newface OK:0\r\n")

        self.testMgmtSock2.connect(("127.0.0.1",self.linklayerport))
        self.testMgmtSock2.send("GET /linklayer/newface/127.0.0.1:8000:0 HTTP/1.1\r\n\r\n".encode())
        data = self.testMgmtSock2.recv(1024)
        self.testMgmtSock2.close()


        self.assertEqual(data.decode(),
                         "HTTP/1.1 200 OK \r\n Content-Type: text/html \r\n\r\n newface OK:1\r\n")

        self.testMgmtSock3.connect(("127.0.0.1", self.linklayerport))
        self.testMgmtSock3.send("GET /linklayer/newface/127.0.0.1:9000:0 HTTP/1.1\r\n\r\n".encode())
        data = self.testMgmtSock3.recv(1024)
        self.testMgmtSock3.close()


        self.assertEqual(data.decode(),
                         "HTTP/1.1 200 OK \r\n Content-Type: text/html \r\n\r\n newface OK:0\r\n")

        self.assertEqual(self.linklayer.faceidtable.get_num_entries(), 2)

        self.assertEqual(self.linklayer.faceidtable.get_face_id(AddressInfo(("127.0.0.1", 9000), 0)), 0)
        self.assertEqual(self.linklayer.faceidtable.get_face_id(AddressInfo(("127.0.0.1", 8000), 0)), 1)

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

        self.assertEqual(self.mgmt.fib.find_fib_entry(Name("/test/data")).faceid, 2)
        self.assertEqual(self.mgmt.fib.find_fib_entry(Name("/data/test")).faceid, 3)

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

        self.assertEqual(self.mgmt.cs.find_content_object(Name("/test/data")).content.content, "HelloWorld")
        self.assertEqual(self.mgmt.cs.find_content_object(Name("/data/test")).content.content, "GoodBye")


    def test_add_face_mgmt_client(self):
        """Test adding a face using the mgmtclient"""
        self.linklayer.start_process()
        self.mgmt.start_process()
        data = self.mgmt_client.add_face("127.0.0.1", 9000, 0)
        self.assertEqual(data, "HTTP/1.1 200 OK \r\n Content-Type: text/html \r\n\r\n newface OK:0\r\n")
        self.assertEqual(self.linklayer.faceidtable.get_num_entries(), 1)
        self.assertEqual(self.linklayer.faceidtable.get_address_info(0), AddressInfo(("127.0.0.1", 9000), 0))
        self.assertEqual(self.linklayer.faceidtable.get_face_id(AddressInfo(("127.0.0.1", 9000), 0)), 0)

    def test_add_forwarding_rule_mgmt_client(self):
        """Test adding forwarding rule using MgmtClient"""
        self.linklayer.start_process()
        self.mgmt.start_process()

        data = self.mgmt_client.add_forwarding_rule(Name("/test/data"), 2)
        self.assertEqual("HTTP/1.1 200 OK \r\n Content-Type: text/html \r\n\r\n newforwardingrule OK:2\r\n", data)

        time.sleep(1)
        data = self.mgmt_client.add_forwarding_rule(Name("/data/test"), 3)
        self.assertEqual(data, "HTTP/1.1 200 OK \r\n Content-Type: text/html \r\n\r\n newforwardingrule OK:3\r\n")

        self.assertEqual(self.mgmt.fib.find_fib_entry(Name("/test/data")).faceid, 2)
        self.assertEqual(self.mgmt.fib.find_fib_entry(Name("/data/test")).faceid, 3)

    def test_mgmt_add_content_mgmt_client(self):
        """Test adding content using MgmtClient"""
        self.linklayer.start_process()
        self.mgmt.start_process()

        data = self.mgmt_client.add_new_content(Name("/test/data"), "HelloWorld")
        self.assertEqual(data, "HTTP/1.1 200 OK \r\n Content-Type: text/html \r\n\r\n newcontent OK\r\n")

        time.sleep(1)
        data = self.mgmt_client.add_new_content(Name("/data/test"), "GoodBye")
        self.assertEqual(data, "HTTP/1.1 200 OK \r\n Content-Type: text/html \r\n\r\n newcontent OK\r\n")

        self.assertEqual(self.mgmt.cs.find_content_object(Name("/test/data")).content.content, "HelloWorld")
        self.assertEqual(self.mgmt.cs.find_content_object(Name("/data/test")).content.content, "GoodBye")

    def test_mgmt_shutdown_mgmt_client(self):
        """Test adding content"""
        self.linklayer.start_process()
        self.mgmt.start_process()
        data = self.mgmt_client.shutdown()
        self.assertEqual(data, "HTTP/1.1 200 OK \r\n Content-Type: text/html \r\n\r\n shutdown\r\n")


    @unittest.skipIf("interfaces not synced yet, no idea how to do that")
    def test_mgmt_new_udp_device_client(self):
        """test if a new udp device is added correctly using the mgmt client"""
        self.linklayer.start_process()
        self.mgmt.start_process()
        test_port = 9008
        data = self.mgmt_client.add_upd_device(test_port)
        self.assertEqual(data, "HTTP/1.1 200 OK \r\n Content-Type: text/html \r\n\r\n newUDPdevice OK:1\r\n")
        self.assertEqual(len(self.linklayer.interfaces), 2)
        self.assertEqual(self.linklayer.interfaces[0].file_descriptor.getsockname()[1], self.linklayer.interfaces[0].get_port())
        self.assertEqual(self.linklayer.interfaces[1].file_descriptor.getsockname()[1], test_port)


