

import unittest

from PiCN.Layers.PacketEncodingLayer.Encoder import NdnTlvEncoder
from PiCN.Packets import Content, Interest, Nack, NackReason, Name, SignatureType

class test_provenienceSignature(unittest.TestCase):
    def setUp(self):
        self.encoder = NdnTlvEncoder()

    def tearDown(self):
        pass

    def test_proviniance_signature(self):
        payload_string="Hello World"
        payload=bytearray(payload_string, 'utf-8')
        name=Name("/test/data")
        enc_data1=self.encoder.encode_data(name, payload, 2,
                                           SignatureType.PROVENANCE_SIGNATURE)
        enc_data2 = self.encoder.encode_data(name, payload, 2,
                                             SignatureType.PROVENANCE_SIGNATURE, None,
                                             self.encoder.get_provenance_for_testing(payload, Name("/test/data/obj1"), 2))
        self.assertNotEqual(enc_data1,enc_data2)
        self.assertTrue(self.encoder.is_content(enc_data2))
        self.assertFalse(self.encoder.is_interest(enc_data2))
        self.assertFalse(self.encoder.is_nack(enc_data2))

        dec_data1=self.encoder.decode(enc_data1)
        dec_data2=self.encoder.decode(enc_data2)


        #self.assertEquals(dec_data1.name,dec_data2.name)
        #self.assertEquals(type(dec_data1.name), type(name))