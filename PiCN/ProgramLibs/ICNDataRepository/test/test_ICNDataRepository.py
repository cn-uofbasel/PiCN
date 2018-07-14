"""Test the ICN Data Repository using fetch"""

import abc
import os
import shutil
import unittest

from PiCN.Layers.PacketEncodingLayer.Encoder import SimpleStringEncoder, NdnTlvEncoder
from PiCN.Packets import Name, NackReason
from PiCN.ProgramLibs.Fetch import Fetch
from PiCN.ProgramLibs.ICNDataRepository import ICNDataRepository


class cases_ICNDataRepository(object):
    """Test the ICN Data Repository using fetch"""

    @abc.abstractmethod
    def get_encoder(self):
        """returns the encoder to be used """

    def setUp(self):
        self.data1 = "data1"
        self.data2 = 'A' * 5000
        self.data3 = 'B' * 20000
        self.encoder = self.get_encoder()

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

        self.ICNRepo: ICNDataRepository = ICNDataRepository("/tmp/repo_unit_test", Name("/test/data"), 0,
                                                            encoder=self.get_encoder(), log_level=255)
        self.repo_port = self.ICNRepo.linklayer.interfaces[0].get_port()
        self.fetch = Fetch("127.0.0.1", self.repo_port, encoder=self.get_encoder())

    def tearDown(self):
        try:
            shutil.rmtree(self.path)
            os.remove("/tmp/repo_unit_test")
        except:
            pass
        self.ICNRepo.stop_repo()
        self.fetch.stop_fetch()

    def test_fetch_single_data(self):
        """Test fetching a single data object without chunking"""
        self.ICNRepo.start_repo()
        content = self.fetch.fetch_data(Name("/test/data/f1"))
        self.assertEqual(content, self.data1)

    def test_fetch_small_data(self):
        """Test fetching a small data object with little chunking"""
        self.ICNRepo.start_repo()
        content = self.fetch.fetch_data(Name("/test/data/f2"))
        self.assertEqual(content, self.data2)

    def test_fetch_big_data(self):
        """Test fetching a big data object with lot of chunking"""
        self.ICNRepo.start_repo()
        content = self.fetch.fetch_data(Name("/test/data/f3"))
        self.assertEqual(content, self.data3)

    def test_fetch_nack(self):
        """Test fetching content which is not available and get nack"""
        self.ICNRepo.start_repo()
        content = self.fetch.fetch_data(Name("/test/data/f4"))
        self.assertEqual(content, "Received Nack: " + NackReason.NO_CONTENT.value)


class test_ICNDataRepository_SimplePacketEncoder(cases_ICNDataRepository, unittest.TestCase):
    """Runs tests with the SimplePacketEncoder"""

    def get_encoder(self):
        return SimpleStringEncoder()


class test_ICNDataRepository_NDNTLVPacketEncoder(cases_ICNDataRepository, unittest.TestCase):
    """Runs tests with the NDNTLVPacketEncoder"""

    def get_encoder(self):
        return NdnTlvEncoder()
