"""Test Name Object"""
import unittest

from PiCN.Packets import Name

class TestContent(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_names_equal(self):
        """Test if two names are equal"""
        n1 = Name("/test/data")
        n2 = Name("/test/data")
        self.assertEqual(n1, n2)

    def test_names_not_equal_name(self):
        """Test if two names objects are not equal: name"""
        n1 = Name("/test/data")
        n2 = Name("/test/data1")
        self.assertNotEqual(n1, n2)
