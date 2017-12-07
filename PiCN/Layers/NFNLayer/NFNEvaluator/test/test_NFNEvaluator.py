"""Tests for the NFNEvaluator"""

import multiprocessing
import unittest

from PiCN.Packets import Interest, Content, Name

from PiCN.Layers.NFNLayer.NFNEvaluator import NFNEvaluator
from PiCN.Layers.NFNLayer.NFNEvaluator.NFNOptimizer import ToDataFirstOptimizer
from PiCN.Layers.NFNLayer.NFNEvaluator.NFNExecutor import NFNPythonExecutor
from PiCN.Layers.ICNLayer.ContentStore import ContentStoreMemoryExact
from PiCN.Layers.ICNLayer.ForwardingInformationBase import ForwardingInformationBaseMemoryPrefix
from PiCN.Layers.ICNLayer.PendingInterestTable import PendingInterstTableMemoryExact

class testNFNEvaluator(unittest.TestCase):
    """Tests for the NFNEvaluator"""

    def setUp(self):
        self.manager = multiprocessing.Manager()
        self.cs: ContentStoreMemoryExact = ContentStoreMemoryExact(self.manager)
        self.fib: ForwardingInformationBaseMemoryPrefix = ForwardingInformationBaseMemoryPrefix(self.manager)
        self.pit: PendingInterstTableMemoryExact = PendingInterstTableMemoryExact(self.manager)
        self.optimizer = ToDataFirstOptimizer(None, self.cs, self.fib, self.pit)
        self.executor = NFNPythonExecutor()
        self.evaluator = NFNEvaluator(None, self.cs, self.fib, self.pit)
        self.evaluator.executor["PYTHON"] = self.executor
        pass

    def tearDown(self):
        if self.evaluator.process:
            self.evaluator.stop_process()
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


    def test_local_execution_no_param(self):
        """Test executing a function with no parameter"""
        fname = Name("/func/f1")
        name = Name("/func/f1")
        name.components.append("_()")
        name.components.append("NFN")
        interest = Interest(name)

        self.evaluator.interest = interest
        self.evaluator.start_process()
        request = self.evaluator.computation_out_queue.get()
        self.assertEqual(request.name, fname)

        func1 = """PYTHON
f
def f():
    return "Hello World" 
        """
        content = Content(fname, func1)
        self.evaluator.computation_in_queue.put(content)
        res = self.evaluator.computation_out_queue.get()
        self.assertEqual(res.content, "Hello World")

    def test_local_execution_data_param(self):
        """Test executing a function with data as parameter"""
        dname = Name("/test/data")
        data = Content(dname, "hello world")

        fname = Name("/func/f1")
        name = Name("/func/f1")
        name.components.append("_(/test/data)")
        name.components.append("NFN")
        interest = Interest(name)
        self.evaluator.interest = interest
        self.evaluator.start_process()
        request = self.evaluator.computation_out_queue.get()
        self.assertEqual(request.name, dname)
        self.evaluator.computation_in_queue.put(data)
        request = self.evaluator.computation_out_queue.get()
        self.assertEqual(request.name, fname)

        func1 = """PYTHON
f
def f(a):
    return a.upper() 
                """
        content = Content(fname, func1)
        self.evaluator.computation_in_queue.put(content)
        res = self.evaluator.computation_out_queue.get()
        self.assertEqual(res.content, "HELLO WORLD")

    def test_local_execution_function_param(self):
        """Test executing a function with data as parameter"""
        fname1 = Name("/func/f1")
        name1 = Name("/func/f1")
        name1.components.append("_(/func/f2(/test/data))")
        name1.components.append("NFN")
        interest = Interest(name1)
        name2 = Name("/func/f2")
        name2.components.append("_(/test/data)")
        name2.components.append("NFN")
        self.evaluator.interest = interest
        self.evaluator.start_process()
        request = self.evaluator.computation_out_queue.get()
        self.assertEqual(request.name, name2)
        subresult = Content(name2, "RESULT")
        func1 = """PYTHON
f
def f(a):
    return a.lower() 
                """
        self.evaluator.computation_in_queue.put(subresult)
        request = self.evaluator.computation_out_queue.get()
        self.assertEqual(request.name, fname1)
        fcontent = Content(fname1, func1)
        self.evaluator.computation_in_queue.put(fcontent)

        res = self.evaluator.computation_out_queue.get()
        self.assertEqual(res.content, "result")

