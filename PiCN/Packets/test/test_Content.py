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

    def test_payload_to_string(self):
        # paylaod can not be decoded with utf-8 codec
        c1 = Content("/test/data", bytes([0x00, 0xb1, 0x01])) # note: this payload can not be decoded with utf-8 codec
        payload_as_string1 = c1.content
        self.assertEqual("0x00 0xb1 0x01", payload_as_string1)
        # paylaod not be decoded with utf-8 codec
        c2 = Content("/test/data", "the-payload")
        payload_as_string2 = c2.content
        self.assertEqual("the-payload", payload_as_string2)
