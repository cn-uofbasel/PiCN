"""Test the TimeoutR2CClient"""

import unittest

from PiCN.Packets import Name, Content, Interest
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

    def test_handle_r2c_request(self):
        """test the handling of r2c messages"""

        name = Name("/test/NFN")
        comp_list = NFNComputationList(self.r2cClient)
        comp_list.add_computation(name, 1, Interest(name))
        r2c_request = self.r2cClient.R2C_create_message(name)
        c = self.r2cClient.R2C_handle_request(r2c_request, comp_list)
        self.assertEqual(c, Content(r2c_request, "Running"))
