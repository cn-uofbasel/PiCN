"""Test a fetch from a repo over an ICN forwarder"""

import os
import shutil
import time
import unittest
from random import randint

from PiCN.ProgramLibs.Fetch import Fetch
from PiCN.ProgramLibs.ICNForwarder import ICNForwarder

from PiCN.Mgmt import MgmtClient
from PiCN.Packets import Name
from PiCN.ProgramLibs.ICNDataRepository import ICNDataRepository


class test_Fetch(unittest.TestCase):

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

        self.ICNRepo: ICNDataRepository = ICNDataRepository("/tmp/repo_unit_test", Name("/test/data"), port=0)
        self.forwarder: ICNForwarder = ICNForwarder(port=0)

        self.repo_port = self.ICNRepo.linklayer.get_port()
        self.forwarder_port = self.forwarder.linklayer.get_port()
        self.fetch = Fetch("127.0.0.1", self.forwarder_port)

    def add_face_and_forwadingrule(self):
        #create new face
        self.mgmtClient = MgmtClient(self.forwarder_port)
        self.mgmtClient.add_face("127.0.0.1", self.repo_port)
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
        self.forwarder2: ICNForwarder = ICNForwarder(0)
        self.ICNRepo.start_repo()
        self.forwarder.start_forwarder()
        self.forwarder2.start_forwarder()

        #check for nack on first route
        self.mgmtClient = MgmtClient(self.forwarder_port)
        self.mgmtClient.add_face("127.0.0.1", self.forwarder2.linklayer.get_port())
        data = self.mgmtClient.add_forwarding_rule(Name("/test/data"), 0)
        nack = self.fetch.fetch_data(Name("/test/data/f3"))
        self.assertEqual(nack, "Received Nack: No FIB Entry")
        time.sleep(0.1)

        #install second forwarding rule and check for result.
        data = self.mgmtClient.add_face("127.0.0.1", self.repo_port)
        self.mgmtClient.add_forwarding_rule(Name("/test"), 2)
        time.sleep(0.1)
        #fetch2 = Fetch("127.0.0.1", 8000 + self.portoffset)
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









