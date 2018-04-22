"""Test the TimeoutR2CClient"""

import unittest

from PiCN.Packets import Name
from PiCN.Layers.NFNLayer.R2C import TimeoutR2CHandler
from PiCN.Layers.NFNLayer.NFNComputationTable import NFNComputationList

class test_TimeoutR2CClient(unittest.TestCase):

    def setUp(self):
        self.r2cClient = TimeoutR2CHandler()

    def test_create_r2c_message(self):
        """test the creation of r2c names"""
        name = Name("/test/NFN")
        new_name = self.r2cClient.R2C_create_message(name)
        compare_name = Name("/test/R2C/KEEPALIVE/NFN")
        self.assertEqual(compare_name, new_name)

    def test_get_original_r2c_message(self):
        """test the creation of r2c names"""
        name = Name("/test/R2C/KEEPALIVE/NFN")
        compare_name = Name("/test/NFN")
        new_name = self.r2cClient.R2C_get_original_message(name)
        self.assertEqual(compare_name, new_name)