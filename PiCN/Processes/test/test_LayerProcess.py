"""Test the Abstract Class LayerProcess"""

import unittest
from multiprocessing import Queue

from PiCN.Processes import LayerProcess


class LayerMock(LayerProcess):
    """ Mock implementation of a LayerProcess """

    def __init__(self):
        LayerProcess.__init__(self)

    def data_from_lower(self, to_lower: Queue, to_higher: Queue, data):
        to_higher.put(data)

    def data_from_higher(self, to_lower: Queue, to_higher: Queue, data):
        to_lower.put(data)


class TestLayerProcess(unittest.TestCase):
    """Test the Abstract Class LayerProcess"""

    def setUp(self):
        self.q1_fromHiger: Queue = Queue()
        self.q2_fromLower: Queue = Queue()
        self.q3_toHigher: Queue = Queue()
        self.q4_toLower: Queue = Queue()

        self.layer: LayerMock = LayerMock()
        self.layer.queue_from_higher = self.q1_fromHiger
        self.layer.queue_from_lower = self.q2_fromLower
        self.layer.queue_to_higher = self.q3_toHigher
        self.layer.queue_to_lower = self.q4_toLower

    def tearDown(self):
        self.layer.stop_process()

    def test_from_higher_to_lower(self):
        """ Test correct handling from Higher to Lower """
        self.layer.start_process()
        self.q1_fromHiger.put("Testdata")
        output = self.q4_toLower.get()
        self.assertEqual(output, "Testdata")

    def test_from_lower_to_higher(self):
        """ Test correct handling from Lower to Higher"""
        self.layer.start_process()
        self.q2_fromLower.put("Testdata")
        output = self.q3_toHigher.get()
        self.assertEqual(output, "Testdata")
