"""Characterization tests for BasicICNLayer.data_from_lower / data_from_higher.

These tests record the CURRENT, observed behaviour of ``BasicICNLayer`` before
the asyncio migration (see
docs/design-adrs/ADR-001-baseline-first-migration.md). They intentionally
describe what the code does today, not what it should do. Once Phase 2 makes
``data_from_lower``/``data_from_higher`` coroutines (ADR-003), this file's
assertions are the contract the rewritten methods must still satisfy.

Per Task 0.7:
- The handlers are called directly (not through the multiprocessing run loop).
- ``queue.Queue`` stands in for the inter-layer queues; no multiprocessing is
  used anywhere in this file.
- Data structures (CS/FIB/PIT) are plain, single-process instances -- the
  same classes ``BasicICNLayer`` uses in production, just without the
  ``multiprocessing.Manager`` proxying that real deployments add for
  cross-process sharing (irrelevant to the layer's routing logic).
"""

import queue
import unittest

from PiCN.Layers.ICNLayer import BasicICNLayer
from PiCN.Layers.ICNLayer.ContentStore import ContentStoreMemoryExact
from PiCN.Layers.ICNLayer.ForwardingInformationBase import ForwardingInformationBaseMemoryPrefix
from PiCN.Layers.ICNLayer.PendingInterestTable import PendingInterstTableMemoryExact
from PiCN.Packets import Content, Interest, Name, Nack, NackReason


class test_BasicICNLayerCharacterization(unittest.TestCase):
    """Locks in BasicICNLayer's current data_from_lower behaviour."""

    def setUp(self):
        self.icn_layer = BasicICNLayer(log_level=255)
        self.icn_layer.cs = ContentStoreMemoryExact()
        self.icn_layer.fib = ForwardingInformationBaseMemoryPrefix()
        self.icn_layer.pit = PendingInterstTableMemoryExact()

        # Plain queue.Queue stand-ins -- data_from_lower/data_from_higher are
        # called directly below, never through start_process()/the run loop.
        self.to_lower = queue.Queue()
        self.to_higher = queue.Queue()

    def test_interest_from_lower_with_fib_entry_is_forwarded_to_lower(self):
        """An Interest with a matching FIB entry is forwarded on to_lower,
        addressed to the FIB's face id, and creates a PIT entry keyed on the
        incoming face id."""
        incoming_face_id = 2
        outgoing_face_id = 5
        name = Name("/test/data")
        interest = Interest("/test/data")
        self.icn_layer.fib.add_fib_entry(name, [outgoing_face_id], static=True)

        self.icn_layer.data_from_lower(self.to_lower, self.to_higher, [incoming_face_id, interest])

        # Exactly one packet appears, on to_lower, addressed to the FIB face.
        face_id, packet = self.to_lower.get_nowait()
        self.assertEqual(outgoing_face_id, face_id)
        self.assertEqual(interest, packet)
        self.assertTrue(self.to_lower.empty())
        self.assertTrue(self.to_higher.empty())

        # A PIT entry now exists, recording the face the Interest came from.
        pit_entry = self.icn_layer.pit.find_pit_entry(name)
        self.assertIsNotNone(pit_entry)
        self.assertIn(incoming_face_id, pit_entry.faceids)

    def test_interest_from_lower_with_no_fib_entry_yields_nack_to_lower(self):
        """An Interest matching nothing (no CS, no PIT, no FIB entry) produces
        a NO_ROUTE Nack sent back on to_lower to the face it arrived from.

        Note: data_from_lower always calls handle_interest_from_lower with
        from_local=False, so the Nack goes to `to_lower`, never `to_higher`,
        regardless of where the Interest logically originated. This looks
        like it could surprise a caller that passed a "local" face id, but it
        is what the code does today.
        """
        incoming_face_id = 7
        interest = Interest("/no/such/route")

        self.icn_layer.data_from_lower(self.to_lower, self.to_higher, [incoming_face_id, interest])

        face_id, packet = self.to_lower.get_nowait()
        self.assertEqual(incoming_face_id, face_id)
        self.assertIsInstance(packet, Nack)
        self.assertEqual(NackReason.NO_ROUTE, packet.reason)
        self.assertEqual(interest.name, packet.name)
        self.assertTrue(self.to_lower.empty())
        self.assertTrue(self.to_higher.empty())

        # No PIT entry survives a Nack'd Interest with no route.
        self.assertIsNone(self.icn_layer.pit.find_pit_entry(interest.name))

    def test_content_from_lower_matching_pit_entry_is_forwarded_to_lower(self):
        """A Content object matching an existing PIT entry is forwarded to
        every face recorded in that PIT entry, the PIT entry is removed, and
        the object is cached in the Content Store."""
        name = Name("/test/data")
        interest = Interest("/test/data")
        waiting_face_id = 3
        arriving_face_id = 9
        content = Content("/test/data", "payload")

        # Seed a PIT entry as if an Interest had already passed through.
        self.icn_layer.pit.add_pit_entry(name, waiting_face_id, interest, local_app=False)

        self.icn_layer.data_from_lower(self.to_lower, self.to_higher, [arriving_face_id, content])

        face_id, packet = self.to_lower.get_nowait()
        self.assertEqual(waiting_face_id, face_id)
        self.assertEqual(content, packet)
        self.assertTrue(self.to_lower.empty())
        self.assertTrue(self.to_higher.empty())

        # The PIT entry is consumed and the object is now cached.
        self.assertIsNone(self.icn_layer.pit.find_pit_entry(name))
        cs_entry = self.icn_layer.cs.find_content_object(name)
        self.assertIsNotNone(cs_entry)
        self.assertEqual(content, cs_entry.content)

    def test_content_from_lower_with_no_pit_entry_is_silently_dropped(self):
        """Unsolicited Content (no matching PIT entry) produces nothing on
        either queue and is not cached. This matches normal ICN behaviour
        (only requested data is accepted) -- not a bug, but worth locking in
        since a naive re-implementation could accidentally start caching
        unsolicited content."""
        content = Content("/nobody/asked/for/this", "payload")

        self.icn_layer.data_from_lower(self.to_lower, self.to_higher, [1, content])

        self.assertTrue(self.to_lower.empty())
        self.assertTrue(self.to_higher.empty())
        self.assertIsNone(self.icn_layer.cs.find_content_object(content.name))


if __name__ == "__main__":
    unittest.main()
