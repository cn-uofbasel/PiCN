"""Test Nack Object"""
import unittest

from PiCN.Packets import Nack

class TestNack(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_content_equal(self):
        """Test if two content objects are equal"""
        nack1 = Nack("/test/data", reason="HelloWorld")
        nack2 = Nack("/test/data", reason="HelloWorld")
        self.assertEqual(nack1, nack2)

    def test_content_not_equal(self):
        """Test if two content objects are not equal"""
        nack1 = Nack("/test/data", reason="HelloWorld")
        nack2 = Nack("/test/data", reason="HelloWorld2")
        self.assertNotEqual(nack1, nack2)