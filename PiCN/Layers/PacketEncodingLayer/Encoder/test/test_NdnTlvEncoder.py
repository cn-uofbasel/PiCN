"""Test the NdnTlvEncoder"""

import unittest

from PiCN.Layers.PacketEncodingLayer.Encoder import NdnTlvEncoder
from PiCN.Packets import Content, Interest, Nack, NackReason, Name

class test_NdnTlvEncoder(unittest.TestCase):
    """Test the NdnTlvEncoder"""

    def setUp(self):
        self.encoder = NdnTlvEncoder()

    def tearDown(self):
        pass

    def test_Interest_Creation_no_wireformat(self):
        """Test the creation of an interest message with no wireformat given"""
        name: Name = Name("/test/data")
        i1: Interest = Interest(name)
        enc_i1 = self.encoder.encode(i1)
        self.assertEqual(enc_i1[0], 0x5)
        self.assertTrue(self.encoder.is_interest(enc_i1))
        self.assertFalse(self.encoder.is_content(enc_i1))
        self.assertFalse(self.encoder.is_nack(enc_i1))
        dec_i1 = self.encoder.decode(enc_i1)
        self.assertEqual(dec_i1, i1)

    def test_Content_Creation_no_wireformat(self):
        """Test the creation of a content object message with no wireformat given"""
        name: Name = Name("/test/data")
        c1: Content =  Content(name, "HelloWorld")
        enc_c1 = self.encoder.encode(c1)
        self.assertEqual(enc_c1[0], 0x6)
        self.assertFalse(self.encoder.is_interest(enc_c1))
        self.assertTrue(self.encoder.is_content(enc_c1))
        self.assertFalse(self.encoder.is_nack(enc_c1))
        dec_c1 = self.encoder.decode(enc_c1)
        self.assertEqual(dec_c1, c1)

    def test_Nack_Creation_no_wireformat(self):
        """Test the creation of a nack object message with no wireformat given"""
        name: Name = Name("/test/data")
        i1: Interest = Interest(name)
        n1: Nack = Nack(name, NackReason.NO_ROUTE, interest=i1)
        enc_n1 = self.encoder.encode(n1)
        print(enc_n1)
        self.assertEqual(enc_n1[0], 0x64)
        self.assertEqual(enc_n1[3], 0x03)
        self.assertEqual(enc_n1[4], 0x20)
        self.assertFalse(self.encoder.is_interest(enc_n1))
        self.assertFalse(self.encoder.is_content(enc_n1))
        self.assertTrue(self.encoder.is_nack(enc_n1))
        dec_n1 = self.encoder.decode(enc_n1)
        self.assertEqual(dec_n1, n1)