"""Test Nack Object"""
import unittest

from PiCN.Packets import Nack
from PiCN.Packets import Interest

class TestNack(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_content_equal(self):
        """Test if two content objects are equal"""
        interest = Interest("/test/data")
        nack1 = Nack("/test/data", reason="HelloWorld", interest=interest)
        nack2 = Nack("/test/data", reason="HelloWorld", interest=interest)
        self.assertEqual(nack1, nack2)

    def test_content_not_equal(self):
        """Test if two content objects are not equal"""
        interest = Interest("/test/data")
        nack1 = Nack("/test/data", reason="HelloWorld", interest=interest)
        nack2 = Nack("/test/data", reason="HelloWorld2", interest=interest)
        self.assertNotEqual(nack1, nack2)