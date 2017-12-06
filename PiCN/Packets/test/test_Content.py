"""Test Content Object"""
import unittest

from PiCN.Packets import Content

class TestContent(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_content_equal(self):
        """Test if two content objects are equal"""
        c1 = Content("/test/data", "HelloWorld")
        c2 = Content("/test/data", "HelloWorld")
        self.assertEqual(c1, c2)

    def test_content_not_equal(self):
        """Test if two content objects are not equal"""
        c1 = Content("/test/data", "HelloWorld")
        c2 = Content("/test/data", "HelloWorld2")
        self.assertNotEqual(c1, c2)