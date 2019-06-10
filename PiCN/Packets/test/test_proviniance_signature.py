"""test proviniance signature"""

import unittest
from PiCN.Packets import Signature,SignatureType

class TestProvinianceSignature(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_empty_signature_equal(self):
        s1=Signature()
        s2=Signature(SignatureType.NO_SIGNATURE,None,None,None,None,None,None)
        self.assertEqual(s1.to_string(), s2.to_string())
        self.assertEqual(s1.to_bytearray(),s2.to_bytearray())

    def test_not_equal(self):
        s1=Signature()
        s2=Signature(SignatureType.PROVENIENCE_SIGNATURE)
        self.assertNotEqual(s1,s2)
        self.assertNotEqual(s1.to_string(), s2.to_string())
        self.assertNotEqual(s1.to_bytearray(), s2.to_bytearray())

    def test_to_bytarray(self):
        s1 = Signature()
        s2 = Signature(SignatureType.NO_SIGNATURE, None, None, None, None, None, None)
        s3 = Signature(SignatureType.PROVENIENCE_SIGNATURE)
        self.assertEqual(s1.to_bytearray(), s2.to_bytearray())
        self.assertNotEqual(s3.to_bytearray(), s2.to_bytearray())

    def test_signatureType(self):
        s1=Signature(SignatureType.PROVENIENCE_SIGNATURE)
        s2 = Signature()
        s3 = Signature(SignatureType.DEFAULT_SIGNATURE)
        self.assertEqual(s1.signatureType,SignatureType.PROVENIENCE_SIGNATURE)
        self.assertEqual(s2.signatureType, SignatureType.NO_SIGNATURE)
        self.assertEqual(s3.signatureType, SignatureType.DEFAULT_SIGNATURE)

