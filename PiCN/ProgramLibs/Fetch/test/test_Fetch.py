"""Test a fetch from a repo over an ICN forwarder"""

import abc
import os
import shutil
import time
import unittest

from PiCN.ProgramLibs.Fetch import Fetch
from PiCN.ProgramLibs.ICNForwarder import ICNForwarder

from PiCN.Mgmt import MgmtClient
from PiCN.Packets import Name, NackReason
from PiCN.Layers.PacketEncodingLayer.Encoder import SimpleStringEncoder, NdnTlvEncoder
from PiCN.ProgramLibs.ICNDataRepository import ICNDataRepository

class cases_Fetch(object):

    @abc.abstractmethod
    def get_encoder(self):
        """get the packet encoder to be used"""

    def setUp(self):
        self.data1 = "data1"
        self.data2 = 'A' * 5000
        self.data3 = 'B' * 20000

        self.path = "/tmp/repo_unit_test"
        try:
            os.stat(self.path)
        except:
            os.mkdir(self.path)
        with open(self.path + "/f1", 'w+') as content_file:
            content_file.write(self.data1)
        with open(self.path + "/f2", 'w+') as content_file:
            content_file.write(self.data2)
        with open(self.path + "/f3", 'w+') as content_file:
            content_file.write('B' * 20000)

        self.ICNRepo: ICNDataRepository = ICNDataRepository("/tmp/repo_unit_test", Name("/test/data"), port=0,
                                                            encoder=self.get_encoder(), log_level=255)
        self.forwarder: ICNForwarder = ICNForwarder(port=0, encoder=self.get_encoder(), log_level=255)

        self.repo_port = self.ICNRepo.linklayer.interfaces[0].get_port()
        self.forwarder_port = self.forwarder.linklayer.interfaces[0].get_port()
        self.fetch = Fetch("127.0.0.1", self.forwarder_port, encoder=self.get_encoder())

    def add_face_and_forwadingrule(self):
        #create new face
        self.mgmtClient = MgmtClient(self.forwarder_port)
        self.mgmtClient.add_face("127.0.0.1", self.repo_port, 0)
        self.mgmtClient.add_forwarding_rule(Name("/test"), faceid=0)

    def tearDown(self):
        try:
            shutil.rmtree(self.path)
            os.remove(self.path)
        except:
            pass
        self.mgmtClient.shutdown()
        self.ICNRepo.stop_repo()
        self.forwarder.stop_forwarder()
        self.fetch.stop_fetch()
        time.sleep(0.5)

    def test_fetch_single_data_over_forwarder(self):
        """Test fetching a single data object over a forwarder without chunking"""
        self.ICNRepo.start_repo()
        self.forwarder.start_forwarder()
        time.sleep(0.1)
        self.add_face_and_forwadingrule()

        content = self.fetch.fetch_data(Name("/test/data/f1"))
        self.assertEqual(content, self.data1)

    def test_fetch_small_data_over_forwarder(self):
        """Test fetching a small data object over a forwarder with little chunking"""
        self.ICNRepo.start_repo()
        self.forwarder.start_forwarder()
        time.sleep(0.1)
        self.add_face_and_forwadingrule()

        content = self.fetch.fetch_data(Name("/test/data/f2"))
        self.assertEqual(content, self.data2)

    def test_fetch_large_data_over_forwarder(self):
        """Test fetching a large data object over a forwarder with more chunking"""
        self.ICNRepo.start_repo()
        self.forwarder.start_forwarder()
        time.sleep(0.1)
        self.add_face_and_forwadingrule()

        content = self.fetch.fetch_data(Name("/test/data/f3"))
        self.assertEqual(content, self.data3)

    def test_fetching_content_from_second_repo_after_nack(self):
        """Test sending an interest to forwarder with no matching content, choose second route to fetch content"""
        self.forwarder2: ICNForwarder = ICNForwarder(0,  encoder=self.get_encoder(), log_level=255)
        self.ICNRepo.start_repo()
        self.forwarder.start_forwarder()
        self.forwarder2.start_forwarder()

        #check for nack on first route
        self.mgmtClient = MgmtClient(self.forwarder_port)
        self.mgmtClient.add_face("127.0.0.1", self.forwarder2.linklayer.interfaces[0].get_port(), 0)
        data = self.mgmtClient.add_forwarding_rule(Name("/test/data"), 0)
        nack = self.fetch.fetch_data(Name("/test/data/f3"))
        self.assertEqual(nack, "Received Nack: " + NackReason.NO_ROUTE.value)
        time.sleep(0.1)

        #install second forwarding rule and check for result.
        data = self.mgmtClient.add_face("127.0.0.1", self.repo_port, 0)
        self.mgmtClient.add_forwarding_rule(Name("/test"), 2)
        time.sleep(0.1)
        fetch2 = Fetch("127.0.0.1", self.forwarder_port)
        content = self.fetch.fetch_data(Name("/test/data/f3"))
        self.assertEqual(content, self.data3)
        self.forwarder2.stop_forwarder()

    def test_fetching_a_lot_of_packets(self):
        """sending a lot of packets using a forwarder and chunking"""
        self.ICNRepo.start_repo()
        self.forwarder.start_forwarder()
        self.add_face_and_forwadingrule()
        self.path = "/tmp/repo_unit_test"
        try:
            os.stat(self.path)
        except:
            os.mkdir(self.path)

        for i in range(1,1000):
            name = "/f" + str(i)
            with open(self.path + name, 'w+') as content_file:
                content_file.write(self.data3)

        for i in range(1,1000):
            fname = "/f" + str(i)
            icn_name = "/test/data" + name
            content = self.fetch.fetch_data(Name(icn_name))
            self.assertEqual(content, self.data3)


class test_Fetch_SimplePacketEncoder(cases_Fetch, unittest.TestCase):
    """Runs tests with the SimplePacketEncoder"""
    def get_encoder(self):
        return SimpleStringEncoder()

class test_Fetch_NDNTLVPacketEncoder(cases_Fetch, unittest.TestCase):
    """Runs tests with the NDNTLVPacketEncoder"""
    def get_encoder(self):
        return NdnTlvEncoder()
