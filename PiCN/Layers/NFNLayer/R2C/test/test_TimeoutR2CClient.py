"""Test the TimeoutR2CClient"""

import unittest

from PiCN.Packets import Name
from PiCN.Layers.NFNLayer.R2C import TimeoutR2CClient

class test_TimeoutR2CClient(unittest.TestCase):

    def setUp(self):
        self.r2cClient = TimeoutR2CClient()

    def test_create_r2c_message(self):
        """test the creation of r2c names"""
        name = Name("/test/NFN")
        new_name = self.r2cClient.R2C_create_message(name)
        compare_name = Name("/test/R2C/KEEPALIVE/NFN")
        self.assertEqual(compare_name, new_name)