"""Test the BasicNFNLayer"""

import multiprocessing
import time
import unittest

from PiCN.Packets import Content, Interest
from PiCN.Layers.NFNLayer import BasicNFNLayer

class test_BasicNFNLayer(unittest.TestCase):
    """Test the BasicNFNLayer"""

    def setUp(self):
        self.nfnLayer: BasicNFNLayer = BasicNFNLayer()
        self.nfnLayer.queue_from_lower = multiprocessing.Queue()
        self.nfnLayer.queue_to_lower = multiprocessing.Queue()

    def tearDown(self):
        pass

    def test_add_computation(self):
        """Test the pending computation queue"""
        interest = Interest("/test/data")
        self.nfnLayer.add_computation(interest)
        self.assertEqual(interest, self.nfnLayer._pending_computations.get())

    def test_handle_computation_queue_interest(self):
        """Test the handling of computation queues"""
        interest = Interest("/test/data")
        #todo requires NFNEvaluator
        print("TODO")
        pass

    def test_data_from_lower_interest(self):
        """Test interest from lower"""
        interest = Interest("/test/data")
        self.nfnLayer.start_process()
        self.nfnLayer.queue_from_lower.put([1, interest])
        time.sleep(0.3)
        data = self.nfnLayer._pending_computations.get()
        self.assertEqual(data, interest)

    def test_data_from_lower_content_not_in_request_table(self):
        """Test content from lower"""
        content = Content("/test/data")
        self.nfnLayer.start_process()
        self.nfnLayer.queue_from_lower.put([1, content])
        time.sleep(0.3)
        # todo requires NFNEvaluator
        print("TODO")
        pass

    def test_data_from_lower_content_in_request_table(self):
        """Test content from lower"""
        content = Content("/test/data")
        self.nfnLayer.start_process()
        self.nfnLayer.queue_from_lower.put([1, content])
        time.sleep(0.3)
        # todo requires NFNEvaluator
        print("TODO")
        pass