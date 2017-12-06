"""Tests for the NFNEvaluator"""

import unittest

from PiCN.Packets import Interest, Content

from PiCN.Layers.NFNLayer.NFNEvaluator import NFNEvaluator
from PiCN.Layers.NFNLayer.NFNEvaluator.NFNOptimizer import ToDataFirstOptimizer
from PiCN.Layers.NFNLayer.NFNEvaluator.NFNExecutor import NFNPythonExecutor

class testNFNEvaluator(unittest.TestCase):
    """Tests for the NFNEvaluator"""

    def setUp(self):
        self.optimizer = ToDataFirstOptimizer(None, None, None, None)
        self.executor = NFNPythonExecutor()
        self.evaluator = NFNEvaluator(self.optimizer, None)
        pass

    def tearDown(self):
        pass

    def test_requesting_data(self):
        """Test requesting data from the NFN Layer"""
        interest = Interest("/func/f1(/test/data)")
        self.evaluator.interest = interest
        i_request = Interest("/test/data")
        self.evaluator.request_data(i_request)
        self.assertTrue(i_request.name in self.evaluator.request_table)

    def test_await_data(self):
        """Test requesting awaiting data from the NFN Layer"""
        interest = Interest("/func/f1(/test/data)")
        self.evaluator.interest = interest
        i_request1 = Interest("/test/data")
        i_request2 = Interest("/data/test")
        self.evaluator.request_data(i_request1)
        self.assertTrue(i_request1.name in self.evaluator.request_table)
        self.evaluator.request_data(i_request2)
        self.assertTrue(i_request2.name in self.evaluator.request_table)

        c_comp1 = Content(i_request1.name, "Hello World")
        c_comp2 = Content(i_request2.name, "Good Bye")
        self.evaluator.computation_in_queue.put(c_comp1)
        self.evaluator.computation_in_queue.put(c_comp2)

        c = self.evaluator.await_data([i_request2, i_request1])
        self.assertEqual([c_comp2, c_comp1], c)