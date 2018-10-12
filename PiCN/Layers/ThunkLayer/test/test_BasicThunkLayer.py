"""Tests for the BasicThunkLayer"""

import unittest

from PiCN.Layers.ThunkLayer import BasicThunkLayer
from PiCN.Packets import Name
from PiCN.Processes import LayerProcess
from PiCN.Packets import Interest, Content, Nack, NackReason, Name
from PiCN.Layers.ICNLayer.PendingInterestTable import PendingInterstTableMemoryExact
from PiCN.Layers.ICNLayer.ContentStore import ContentStoreMemoryExact
from PiCN.Layers.ICNLayer.ForwardingInformationBase import ForwardingInformationBaseMemoryPrefix
from PiCN.Layers.LinkLayer.FaceIDTable import FaceIDDict
from PiCN.Layers.NFNLayer.Parser import *

class test_BasicThunkLayer(unittest.TestCase):
    """Tests for the BasicThunkLayer"""

    def setUp(self):
        self.cs = ContentStoreMemoryExact()
        self.fib = ForwardingInformationBaseMemoryPrefix()
        self.pit = PendingInterstTableMemoryExact()
        self.faceidtable = FaceIDDict()
        self.parser = DefaultNFNParser()
        self.thunklayer = BasicThunkLayer(self.cs, self.fib, self.pit, self.faceidtable, self.parser)

    def tearDown(self):
        pass

    def test_remove_thunk_marker(self):
        """Test if the system removes the thunk marker correctly"""
        name = Name("/test/data/THUNK/NFN")
        ret = self.thunklayer.removeThunkMarker(name)
        self.assertEqual(ret, Name("/test/data/NFN"))
        self.assertEqual(name, Name("/test/data/THUNK/NFN"))

        name2 = Name("/test/data/NFN")
        ret = self.thunklayer.removeThunkMarker(name2)
        self.assertEqual(ret, name2)
        self.assertEqual(ret, Name("/test/data/NFN"))

    def test_add_thunk_marker(self):
        """Test if system adds the thunk marker correctly"""
        name = Name("/test/data/NFN")
        ret = self.thunklayer.addThunkMarker(name)
        self.assertEqual(name, Name("/test/data/NFN"))
        self.assertEqual(ret, Name("/test/data/THUNK/NFN"))

        name2 = Name("/test/data/THUNK/NFN")
        ret = self.thunklayer.addThunkMarker(name2)
        self.assertEqual(ret, name2)
        self.assertEqual(ret, Name("/test/data/THUNK/NFN"))

    def test_generating_possible_names(self):
        """Test if the possible thunk names are generated correctly"""
        comp_str = "/func/f1(/func/f2(/test/data/d1),/func/f3(/test/data/d2))"


