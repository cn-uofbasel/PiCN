"""Characterization tests for BasicPacketEncodingLayer handlers.

Locks in CURRENT observed behaviour before/through the extract-core
migration (ADR-001, ADR-003 addendum). Handlers are called directly with
``queue.Queue`` stand-ins -- no multiprocessing.
"""

import queue
import unittest

from PiCN.Layers.PacketEncodingLayer import BasicPacketEncodingLayer
from PiCN.Layers.PacketEncodingLayer.Encoder import SimpleStringEncoder
from PiCN.Packets import Interest


class test_BasicPacketEncodingLayerCharacterization(unittest.TestCase):
    """Locks in BasicPacketEncodingLayer's current handler behaviour."""

    def setUp(self):
        self.layer = BasicPacketEncodingLayer(encoder=SimpleStringEncoder(), log_level=255)
        self.to_lower = queue.Queue()
        self.to_higher = queue.Queue()

    def test_interest_from_higher_is_encoded_to_lower(self):
        interest = Interest("/test/data")
        self.layer.data_from_higher(self.to_lower, self.to_higher, [2, interest])

        face_id, encoded = self.to_lower.get_nowait()
        self.assertEqual(2, face_id)
        self.assertEqual(self.layer.encode(interest), encoded)
        self.assertTrue(self.to_higher.empty())

    def test_encoded_interest_from_lower_is_decoded_to_higher(self):
        interest = Interest("/test/data")
        encoded = self.layer.encode(interest)
        self.layer.data_from_lower(self.to_lower, self.to_higher, [3, encoded])

        face_id, decoded = self.to_higher.get_nowait()
        self.assertEqual(3, face_id)
        self.assertEqual(interest, decoded)
        self.assertTrue(self.to_lower.empty())

    def test_malformed_wrong_length_is_dropped(self):
        self.layer.data_from_higher(self.to_lower, self.to_higher, [1])
        self.assertTrue(self.to_lower.empty())
        self.assertTrue(self.to_higher.empty())

    def test_malformed_non_int_face_id_is_dropped(self):
        self.layer.data_from_lower(self.to_lower, self.to_higher, ["x", b"data"])
        self.assertTrue(self.to_lower.empty())
        self.assertTrue(self.to_higher.empty())
