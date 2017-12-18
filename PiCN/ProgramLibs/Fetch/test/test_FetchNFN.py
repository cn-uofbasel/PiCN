"""Test fetch together with NFN"""

import os
import shutil
import time
import unittest
from random import randint

from PiCN.ProgramLibs.Fetch import Fetch
from PiCN.ProgramLibs.NFNForwarder import NFNForwarder

from PiCN.Mgmt import MgmtClient
from PiCN.Packets import Name
from PiCN.ProgramLibs.ICNDataRepository import ICNDataRepository


class test_Fetch(unittest.TestCase):

    def setUp(self):
        self.data1 = "data1"
        self.data2 = 'a' * 5000
        self.data3 = 'b' * 20000

        self.path = "/tmp/repo_unit_test"
        try:
            os.stat(self.path)
        except:
            os.mkdir(self.path)
        with open(self.path + "/d1", 'w+') as content_file:
            content_file.write(self.data1)
        with open(self.path + "/d2", 'w+') as content_file:
            content_file.write(self.data2)
        with open(self.path + "/d3", 'w+') as content_file:
            content_file.write('b' * 20000)

        self.portoffset = randint(0,999)
        self.ICNRepo: ICNDataRepository = ICNDataRepository("/tmp/repo_unit_test", Name("/test/data"), 10000 + self.portoffset)
        self.forwarder1: NFNForwarder = NFNForwarder(8000 + self.portoffset, debug_level=255)
        self.forwarder2: NFNForwarder = NFNForwarder(9000 + self.portoffset, debug_level=255)
        self.fetch = Fetch("127.0.0.1", 8000 + self.portoffset)

    def add_face_and_forwadingrule(self):
        #create new face
        self.mgmtClient1 = MgmtClient(8000 + self.portoffset)
        self.mgmtClient1.add_face("127.0.0.1", 9000 + self.portoffset)
        self.mgmtClient1.add_forwarding_rule(Name("/lib"), 0)
        self.mgmtClient1.add_face("127.0.0.1", 10000 + self.portoffset)
        self.mgmtClient1.add_forwarding_rule(Name("/test"), 0)

        self.mgmtClient2 = MgmtClient(9000 + self.portoffset)
        self.mgmtClient2.add_face("127.0.0.1", 10000 + self.portoffset)
        self.mgmtClient2.add_forwarding_rule(Name("/test"), 0)

    def tearDown(self):
        try:
            shutil.rmtree(self.path)
            os.remove(self.path)
        except:
            pass
        self.mgmtClient1.shutdown()
        self.mgmtClient2.shutdown()
        self.ICNRepo.stop_repo()
        self.forwarder1.stop_forwarder()
        self.forwarder2.stop_forwarder()
        self.fetch.stop_fetch()

    def test_compute_on_single_data_over_forwarder(self):
        """Test fetch result with single input data"""
        self.ICNRepo.start_repo()
        self.forwarder1.start_forwarder()
        self.forwarder2.start_forwarder()
        time.sleep(0.1)
        self.add_face_and_forwadingrule()
        self.mgmtClient1.add_new_content(Name("/test/data/d1"), self.data1)
        self.mgmtClient2.add_new_content(Name("/lib/func/f1"), "PYTHON\nf\ndef f(a):\n    return a.upper()")
        fetch_name = Name("/lib/func/f1")
        fetch_name.components.append("_(/test/data/d1)")
        fetch_name.components.append("NFN")
        content = self.fetch.fetch_data(fetch_name)
        self.assertEqual(self.data1.upper(), content)

    def test_compute_on_single_data_over_forwarder_data_from_repo(self):
        """Test fetch result with single input data from repo"""
        self.ICNRepo.start_repo()
        self.forwarder1.start_forwarder()
        self.forwarder2.start_forwarder()
        time.sleep(0.1)
        self.add_face_and_forwadingrule()
        self.mgmtClient2.add_new_content(Name("/lib/func/f1"), "PYTHON\nf\ndef f(a):\n    return a.upper()")
        fetch_name = Name("/lib/func/f1")
        fetch_name.components.append("_(/test/data/d1)")
        fetch_name.components.append("NFN")
        content = self.fetch.fetch_data(fetch_name)
        self.assertEqual(self.data1.upper(), content)

    def test_compute_on_large_data_over_forwarder_data_from_repo(self):
        """Test fetch result with large input data from repo"""
        self.ICNRepo.start_repo()
        self.forwarder1.start_forwarder()
        self.forwarder2.start_forwarder()
        time.sleep(0.1)
        self.add_face_and_forwadingrule()
        self.mgmtClient2.add_new_content(Name("/lib/func/f1"), "PYTHON\nf\ndef f(a):\n    return a.upper()")
        fetch_name = Name("/lib/func/f1")
        fetch_name.components.append("_(/test/data/d3)")
        fetch_name.components.append("NFN")
        content = self.fetch.fetch_data(fetch_name)
        self.assertEqual(self.data3.upper(), content)
