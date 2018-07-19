"""Test the ExtendedNdnTlvEncoder"""

import unittest

from PiCN.Packets import Name
from PiCN.Playground.Heartbeats.Layers.PacketEncoding import ExtendedNdnTlvEncoder, Heartbeat


class test_ExtendedNdnTlvEncoder(unittest.TestCase):
    """Test the ExtendedNdnTlvEncoder"""

    def setUp(self):
        self.encoder = ExtendedNdnTlvEncoder()

    def tearDown(self):
        pass

    def test_Heartbeat_Creation_no_wireformat(self):
        """Test the creation of an heartbeat packet with no wireformat given"""
        name: Name = Name("/test/data")
        h1: Heartbeat = Heartbeat(name)
        enc_h1 = self.encoder.encode(h1)
        self.assertEqual(enc_h1[0], 0x02)
        self.assertTrue(self.encoder.is_heartbeat(enc_h1))
        dec_h1 = self.encoder.decode(enc_h1)
        self.assertEqual(dec_h1, h1)