"""Test interest Object"""
import unittest

from PiCN.Packets import Interest

class TestInterest(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_interest_equal(self):
        """Test if two interest objects are equal"""
        i1 = Interest("/test/data")
        i2 = Interest("/test/data")
        self.assertEqual(i1, i2)

    def test_interest_not_equal(self):
        """Test if two interest objects are not equal"""
        i1 = Interest("/test/data")
        i2 = Interest("/test/data2")
        self.assertNotEqual(i1, i2)