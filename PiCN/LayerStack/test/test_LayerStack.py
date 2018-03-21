
import unittest

from PiCN.LayerStack import LayerStack
from PiCN.Layers.ICNLayer import BasicICNLayer
from PiCN.Layers.PacketEncodingLayer import BasicPacketEncodingLayer
from PiCN.Layers.LinkLayer import UDP4LinkLayer
from PiCN.Processes import LayerProcess


class test_LayerStack(unittest.TestCase):

    def test_create_empty(self):
        lstack: LayerStack = LayerStack([])
        self.assertEqual(0, len(lstack.layers))
        self.assertEqual(0, len(lstack.queues))

    def test_create_single(self):
        layer: LayerProcess = LayerProcess()
        lstack: LayerStack = LayerStack([layer])
        self.assertEqual(1, len(lstack.layers))
        self.assertEqual(0, len(lstack.queues))

    def test_create_multiple(self):
        toplayer: LayerProcess = BasicICNLayer()
        middlelayer: LayerProcess = BasicPacketEncodingLayer()
        bottomlayer: LayerProcess = UDP4LinkLayer()
        lstack: LayerStack = LayerStack([
            toplayer,
            middlelayer,
            bottomlayer
        ])
        self.assertEqual(3, len(lstack.layers))
        self.assertEqual(4, len(lstack.queues))
        self.assertEqual(toplayer.queue_to_lower, middlelayer.queue_from_higher)
        self.assertEqual(toplayer.queue_from_lower, middlelayer.queue_to_higher)
        self.assertEqual(middlelayer.queue_to_lower, bottomlayer.queue_from_higher)
        self.assertEqual(middlelayer.queue_from_lower, bottomlayer.queue_to_higher)
        self.assertNotEqual(toplayer.queue_to_lower, bottomlayer.queue_from_higher)
        self.assertNotEqual(toplayer.queue_from_lower, bottomlayer.queue_to_higher)

    def test_insert_empty(self):
        lstack: LayerStack = LayerStack([])
        newlayer: LayerProcess = LayerProcess()
        lstack.insert(newlayer)
        self.assertEqual(1, len(lstack.layers))
        self.assertEqual(newlayer, lstack.layers[0])

    def test_insert_bottom(self):
        toplayer: LayerProcess = BasicICNLayer()
        newlayer: LayerProcess = BasicPacketEncodingLayer()
        lstack: LayerStack = LayerStack([toplayer])
        lstack.insert(newlayer, below_of=toplayer)
        self.assertEqual(2, len(lstack.layers))
        self.assertEqual(toplayer, lstack.layers[0])
        self.assertEqual(newlayer, lstack.layers[1])
        self.assertEqual(toplayer.queue_to_lower, newlayer.queue_from_higher)
        self.assertEqual(toplayer.queue_from_lower, newlayer.queue_to_higher)
        self.assertIsNone(newlayer.queue_to_lower)
        self.assertIsNone(newlayer.queue_from_lower)

    def test_insert_top(self):
        bottomlayer: LayerProcess = UDP4LinkLayer()
        newlayer: LayerProcess = BasicPacketEncodingLayer()
        lstack: LayerStack = LayerStack([bottomlayer])
        lstack.insert(newlayer, on_top_of=bottomlayer)
        self.assertEqual(2, len(lstack.layers))
        self.assertEqual(bottomlayer, lstack.layers[1])
        self.assertEqual(newlayer, lstack.layers[0])
        self.assertEqual(bottomlayer.queue_to_higher, newlayer.queue_from_lower)
        self.assertEqual(bottomlayer.queue_from_higher, newlayer.queue_to_lower)
        self.assertIsNone(newlayer.queue_to_higher)
        self.assertIsNone(newlayer.queue_from_higher)

    def test_insert_between(self):
        toplayer: LayerProcess = BasicICNLayer()
        bottomlayer: LayerProcess = UDP4LinkLayer()
        newlayer: LayerProcess = BasicPacketEncodingLayer()
        lstack: LayerStack = LayerStack([
            toplayer,
            bottomlayer
        ])
        lstack.insert(newlayer, on_top_of=bottomlayer)
        self.assertEqual(3, len(lstack.layers))
        self.assertEqual(toplayer, lstack.layers[0])
        self.assertEqual(newlayer, lstack.layers[1])
        self.assertEqual(bottomlayer, lstack.layers[2])
        self.assertEqual(toplayer.queue_to_lower, newlayer.queue_from_higher)
        self.assertEqual(toplayer.queue_from_lower, newlayer.queue_to_higher)
        self.assertEqual(bottomlayer.queue_to_higher, newlayer.queue_from_lower)
        self.assertEqual(bottomlayer.queue_from_higher, newlayer.queue_to_lower)
        self.assertNotEqual(toplayer.queue_to_lower, bottomlayer.queue_from_higher)
        self.assertNotEqual(toplayer.queue_from_lower, bottomlayer.queue_to_higher)


if __name__ == '__main__':
    unittest.main()
