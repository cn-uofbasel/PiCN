"""Test the SimpleStringEncoder"""

import unittest

from PiCN.Layers.PacketEncodingLayer.Encoder import SimpleStringEncoder
from PiCN.Packets import Content, Interest, Nack, NackReason, Name

class test_SimpleStringEncoder(unittest.TestCase):
    """Test the SimpleStringEncoder"""

    def setUp(self):
        self.encoder1 = SimpleStringEncoder()

    def tearDown(self):
        pass

    def test_Encoder_encode_interest_equal(self):
        """Test the interest encoding of Encoder: equal"""
        i = Interest("/test/data")
        ei = self.encoder1.encode(i)
        self.assertEqual(ei.decode(), "I:/test/data:")

    def test_Encoder_encode_interest_not_equal(self):
        """Test the interest encoding of Encoder: not equal"""
        i = Interest("/data/test")
        ei = self.encoder1.encode(i)
        self.assertNotEqual(ei.decode(), "I:/test/data:")

    def test_Encoder_decode_interest_equal(self):
        """Test the interest decoding of Encoder: equal"""
        data = "I:/test/data:".encode()
        di = self.encoder1.decode(data)
        cmp_interest = Interest("/test/data")
        self.assertTrue(di == cmp_interest)

    def test_Encoder_decode_interest_equal(self):
        """Test the interest decoding of Encoder: not equal"""
        data = "I:/data/test:".encode()
        di = self.encoder1.decode(data)
        cmp_interest = Interest("/test/data")
        self.assertFalse(di == cmp_interest)

    def test_Encoder_encode_decode_interest(self):
        """Test the interest decoding of Encoder: equal"""
        i = Interest("/data/test")
        ei = self.encoder1.encode(i)
        di = self.encoder1.decode(ei)
        self.assertTrue(i == di)

    def test_Encoder_decode_content_equal(self):
        """Test the Content decoding of Encoder: equal"""
        data = "C:/data/test::HelloWorld".encode()
        dc = self.encoder1.decode(data)
        cmp_interest = Content("/data/test", "HelloWorld")
        self.assertTrue(dc == cmp_interest)

    def test_Encoder_decode_content_not_equal(self):
        """Test the Content decoding of Encoder: not equal"""
        data = "C:/data/test::HelloWorld2".encode()
        dc = self.encoder1.decode(data)
        cmp_interest = Content("/data/test", "HelloWorld")
        self.assertFalse(dc == cmp_interest)

    def test_Encoder_encode_decode_content(self):
        """Test the content decoding of Encoder"""
        c = Content("/data/test", "HelloWorld")
        ec = self.encoder1.encode(c)
        dc = self.encoder1.decode(ec)
        self.assertTrue(c == dc)

    def test_Encoder_encode_decode_nack(self):
        """Test the nack decoding of Encoder"""
        interest = Interest("/data/test")
        n = Nack("/data/test", NackReason.NO_CONTENT, interest=interest)
        en = self.encoder1.encode(n)
        dn = self.encoder1.decode(en)
        self.assertTrue(n == dn)