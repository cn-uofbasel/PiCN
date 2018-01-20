"""Test the BasicNFNLayer"""

import multiprocessing
import time
import unittest

from PiCN.Packets import Content, Interest, Name, Nack
from PiCN.Layers.NFNLayer import BasicNFNLayer
from PiCN.Layers.NFNLayer.NFNEvaluator.NFNExecutor import NFNPythonExecutor
from PiCN.Layers.ICNLayer.ContentStore import ContentStoreMemoryExact
from PiCN.Layers.ICNLayer.ForwardingInformationBase import ForwardingInformationBaseMemoryPrefix
from PiCN.Layers.ICNLayer.PendingInterestTable import PendingInterstTableMemoryExact

class test_BasicNFNLayer(unittest.TestCase):
    """Test the BasicNFNLayer"""

    def setUp(self):
        self.manager = multiprocessing.Manager()
        self.cs = ContentStoreMemoryExact(self.manager)
        self.fib = ForwardingInformationBaseMemoryPrefix(self.manager)
        self.pit = PendingInterstTableMemoryExact(self.manager)
        self.executor = {"PYTHON": NFNPythonExecutor}
        self.nfnLayer: BasicNFNLayer = BasicNFNLayer(self.manager, self.cs, self.fib, self.pit, self.executor)
        self.nfnLayer.queue_from_lower = multiprocessing.Queue()
        self.nfnLayer.queue_to_lower = multiprocessing.Queue()

        self.nfnLayer.executor = self.executor

    def tearDown(self):
        self.nfnLayer.stop_process()
        pass

    def test_add_computation(self):
        """Test the pending computation queue"""
        interest = Interest("/test/data")
        running_comps = {}
        for i in range(0,self.nfnLayer._max_running_computations + 1):
            running_comps[i] = i
        self.nfnLayer.add_computation(interest, running_comps)
        self.assertEqual(interest, self.nfnLayer._pending_computations.get()[0])

    def test_data_from_lower_interest(self):
        """Test interest from lower"""
        interest = Interest("/test/data")
        self.nfnLayer.start_process()
        self.nfnLayer.queue_from_lower.put([1, interest])
        time.sleep(0.3)
        data = self.nfnLayer.queue_to_lower.get()
        self.assertEqual([1, interest], data)
        content = Content(interest.name, "Result")
        self.nfnLayer.queue_from_lower.put([3, content])
        data = self.nfnLayer.queue_to_lower.get()
        self.assertEqual([3, content], data)

    def test_fwd_computation(self):
        """Test forwarding of a computation"""
        self.fib.add_fib_entry(Name("/test"), 1, True)
        self.nfnLayer.start_process()
        cid = 1
        name = Name("/test/data")
        name.components.append("/func/f1(_)")
        name.components.append("NFN")
        interest = Interest(name)
        self.nfnLayer.queue_from_lower.put([cid, interest])
        fwded = self.nfnLayer.queue_to_lower.get()
        self.assertEqual(name, fwded[1].name)
        #self.assertEqual(0, len(self.nfnLayer._running_computations)) #todo, remove comp if process dies

    def test_fwd_computation_back(self):
        """Test forwarding of a computation sending data back"""
        self.fib.add_fib_entry(Name("/test"), 1, True)
        self.nfnLayer.start_process()
        cid = 1
        name = Name("/test/data")
        name.components.append("/func/f1(_)")
        name.components.append("NFN")
        interest = Interest(name)
        self.nfnLayer.queue_from_lower.put([cid, interest])
        fwded = self.nfnLayer.queue_to_lower.get()
        self.assertEqual(name, fwded[1].name)
        #self.assertEqual(0, len(self.nfnLayer._running_computations)) #todo, remove comp if process dies
        content = Content(name, "Result")
        self.nfnLayer.queue_from_lower.put([2, content])
        data = self.nfnLayer.queue_to_lower.get()
        self.assertEqual([0, content], data)

    def test_fwd_computation_change_name(self):
        """Test rewriting and forwarding of a computation"""
        self.fib.add_fib_entry(Name("/test"), 1, True)
        self.nfnLayer.start_process()
        cid = 1
        name = Name("/func/f1")
        name.components.append("_(/test/data)")
        name.components.append("NFN")
        name_cmp = Name("/test/data")
        name_cmp.components.append("/func/f1(_)")
        name_cmp.components.append("NFN")
        interest = Interest(name)
        self.nfnLayer.queue_from_lower.put([cid, interest])
        rewritten = self.nfnLayer.queue_to_lower.get()
        self.assertEqual(name_cmp, rewritten[1].name)

    def test_fwd_computation_change_name_map_back(self):
        """Test rewriting and forwarding of a computation, map back"""
        self.fib.add_fib_entry(Name("/test"), 1, True)
        self.nfnLayer.start_process()
        cid = 1
        name = Name("/func/f1")
        name.components.append("_(/test/data)")
        name.components.append("NFN")
        name_cmp = Name("/test/data")
        name_cmp.components.append("/func/f1(_)")
        name_cmp.components.append("NFN")
        interest = Interest(name)
        self.nfnLayer.queue_from_lower.put([cid, interest])
        rewritten = self.nfnLayer.queue_to_lower.get()
        self.assertEqual(name_cmp, rewritten[1].name)
        content = Content(name_cmp, "Result")
        self.nfnLayer.queue_from_lower.put([cid, content])
        mapped_back = self.nfnLayer.queue_to_lower.get()
        self.assertEqual(name, mapped_back[1].name)
        self.assertEqual("Result", mapped_back[1].content)

    def test_compute_simple_function(self):
        """Test if a simple function call is executed correctly"""
        self.nfnLayer.start_process()
        cid = 1
        name = Name("/func/f1")
        name.components.append("_()")
        name.components.append("NFN")
        interest = Interest(name)
        self.nfnLayer.queue_from_lower.put([cid, interest])
        data = self.nfnLayer.queue_to_lower.get()
        self.assertEqual(data[1].name, Name("/func/f1"))
        func1 = """PYTHON
f
def f():
    return "Hello World"        
        """
        func_data = Content(Name("/func/f1"), func1)
        self.nfnLayer.queue_from_lower.put([cid, func_data])
        data = self.nfnLayer.queue_to_lower.get()
        self.assertEqual(name, data[1].name)
        self.assertEqual("Hello World", data[1].content)

    def test_compute_simple_function_with_params(self):
        """Test if a simple function call with params is executed correctly"""
        self.nfnLayer.start_process()
        cid = 1
        name = Name("/func/f1")
        name.components.append("_(/test/data)")
        name.components.append("NFN")
        interest = Interest(name)
        self.nfnLayer.queue_from_lower.put([cid, interest])
        data = self.nfnLayer.queue_to_lower.get()
        self.assertEqual(data[1].name, Name("/test/data"))
        content = Content("/test/data", "result")
        self.nfnLayer.queue_from_lower.put([data[0], content])
        data = self.nfnLayer.queue_to_lower.get()
        self.assertEqual(data[1].name, Name("/func/f1"))
        func1 = """PYTHON
f
def f(a):
    return a.upper()        
        """
        func_data = Content(Name("/func/f1"), func1)
        self.nfnLayer.queue_from_lower.put([cid, func_data])
        data = self.nfnLayer.queue_to_lower.get()
        self.assertEqual(name, data[1].name)
        self.assertEqual("RESULT", data[1].content)

    def test_compute_function_sub_with_params(self):
        """Test if a simple function call with params is executed correctly"""
        self.nfnLayer.start_process()
        cid = 1
        name = Name("/func/f1")
        name.components.append("_(/func/f2(/test/data))")
        name.components.append("NFN")
        interest = Interest(name)
        self.nfnLayer.queue_from_lower.put([cid, interest])
        data = self.nfnLayer.queue_to_lower.get()
        self.assertEqual(data[1].name, Name("/test/data"))
        content = Content("/test/data", "tluser")
        self.nfnLayer.queue_from_lower.put([data[0], content])
        data = self.nfnLayer.queue_to_lower.get()
        self.assertEqual(data[1].name, Name("/func/f2"))
        func2 = """PYTHON
f
def f(a):
    return a.upper()        
        """
        func_data = Content(Name("/func/f2"), func2)
        self.nfnLayer.queue_from_lower.put([cid, func_data])
        data = self.nfnLayer.queue_to_lower.get()
        self.assertEqual(data[1].name, Name("/func/f1"))
        func1 = """PYTHON
f
def f(a):
    return a[::-1]        
                """
        func_data = Content(Name("/func/f1"), func1)
        self.nfnLayer.queue_from_lower.put([cid, func_data])
        data = self.nfnLayer.queue_to_lower.get()
        self.assertEqual(name.to_string(), data[1].name.to_string())
        self.assertEqual("RESULT", data[1].content)

    def test_nack_if_error(self):
        """Test if an error returns a nack"""
        self.nfnLayer.start_process()
        cid = 1
        name = Name("/func/f1")
        name.components.append("_()")
        name.components.append("NFN")
        interest = Interest(name)
        self.nfnLayer.queue_from_lower.put([cid, interest])
        data = self.nfnLayer.queue_to_lower.get()
        self.assertEqual(data[1].name, Name("/func/f1"))
        func1 = """PYTHON
f
def f():
    return fds "Hello World"        
            """
        func_data = Content(Name("/func/f1"), func1)
        self.nfnLayer.queue_from_lower.put([cid, func_data])
        data = self.nfnLayer.queue_to_lower.get()
        self.assertEqual(name, data[1].name)
        self.assertEqual(Nack(name, "Could not Compute"), data[1])

    def test_fwd_computation_nack_stop_fwd_nack(self):
        """Test forwarding of a computation and stop computation"""
        self.fib.add_fib_entry(Name("/test"), 1, True)
        self.nfnLayer.start_process()
        cid = 1
        name = Name("/test/data")
        name.components.append("/func/f1(_)")
        name.components.append("NFN")
        interest = Interest(name)
        self.nfnLayer.queue_from_lower.put([cid, interest])
        fwded = self.nfnLayer.queue_to_lower.get()
        self.assertEqual(name, fwded[1].name)
        #self.assertEqual(0, len(self.nfnLayer._running_computations)) #todo, remove comp if process dies
        nack = Nack(name, "No PIT Entry found")
        self.nfnLayer.queue_from_lower.put([2, nack])
        data = self.nfnLayer.queue_to_lower.get()
        self.assertTrue(isinstance(data[1], Interest))
        self.assertEqual( Name("/test/data"), data[1].name)
        self.nfnLayer.queue_from_lower.put([data[0], nack])
        data = self.nfnLayer.queue_to_lower.get()
        self.assertTrue(isinstance(data[1], Nack))
        self.assertEqual(name, data[1].name)


    def test_fwd_computation_nack_second_path(self):
        """Test forwarding of a computation and applying second rule"""
        self.fib.add_fib_entry(Name("/test"), 1, True)
        self.fib.add_fib_entry(Name("/func"), 2, True)
        self.nfnLayer.start_process()
        cid = 1
        name = Name("/test/data")
        name.components.append("/func/f1(_)")
        name.components.append("NFN")
        interest = Interest(name)
        self.nfnLayer.queue_from_lower.put([cid, interest])
        fwded = self.nfnLayer.queue_to_lower.get()
        self.assertEqual(name, fwded[1].name)
        #self.assertEqual(0, len(self.nfnLayer._running_computations)) #todo, remove comp if process dies
        nack = Nack(name, "No PIT Entry found")
        self.nfnLayer.queue_from_lower.put([2, nack])
        data = self.nfnLayer.queue_to_lower.get()
        name2 = Name("/func/f1")
        name2.components.append("_(/test/data)")
        name2.components.append("NFN")
        self.assertEqual(name2, data[1].name)
        content = Content(name2, "Hello World")
        self.nfnLayer.queue_from_lower.put([2, content])
        data = self.nfnLayer.queue_to_lower.get()
        self.assertEqual(name, data[1].name)
        self.assertEqual("Hello World", data[1].content)