"""Test the BasicNFNLayer"""

import multiprocessing
import time
import unittest

from PiCN.Packets import Content, Interest, Name
from PiCN.Layers.NFNLayer import BasicNFNLayer
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
        self.nfnLayer: BasicNFNLayer = BasicNFNLayer(self.manager, self.cs, self.fib, self.pit)
        self.nfnLayer.queue_from_lower = multiprocessing.Queue()
        self.nfnLayer.queue_to_lower = multiprocessing.Queue()

    def tearDown(self):
        pass

    def test_add_computation(self):
        """Test the pending computation queue"""
        interest = Interest("/test/data")
        self.nfnLayer.add_computation(interest)
        self.assertEqual(interest, self.nfnLayer._pending_computations.get())

    def test_data_from_lower_interest(self):
        """Test interest from lower"""
        interest = Interest("/test/data")
        self.nfnLayer.start_process()
        self.nfnLayer.queue_from_lower.put([1, interest])
        time.sleep(0.3)
        data = self.nfnLayer._pending_computations.get()
        self.assertEqual(data, interest)

    def test_fwd_computation(self):
        """Test rewriting and forwarding of a computation"""
        self.fib.add_fib_entry(Name("/test"), 1, True)
        self.nfnLayer.start_process()
        time.sleep(0.5)
        self.nfnLayer.ageing()
        cid = 1
        name = Name("/test/data")
        name.components.append("/func/f1(_)")
        name.components.append("NFN")
        interest = Interest(name)
        self.nfnLayer.queue_from_lower.put([cid, interest])
        rewritten = self.nfnLayer.queue_to_lower.get()
        self.assertEqual(rewritten.name, name)
