"""Test NFN Forwarder with Thunks"""

import unittest

from PiCN.ProgramLibs.NFNForwarder import NFNForwarder
from PiCN.ProgramLibs.Fetch import Fetch
from PiCN.Layers.PacketEncodingLayer.Encoder import NdnTlvEncoder
from PiCN.Mgmt import MgmtClient
from PiCN.Packets import *

class test_NFNForwarderThunks(unittest.TestCase):
    """Test NFN Forwarder with Thunks"""

#TODO: Add optimizer to execute the plans
#TODO: Add REPO TO TEST

    def get_encoder(self):
        return NdnTlvEncoder()

    def setUp(self):
        self.encoder = self.get_encoder()
        self.forwarder1 = NFNForwarder(0, encoder=self.get_encoder(), log_level=255, use_thunks=True)
        self.forwarder2 = NFNForwarder(0, encoder=self.get_encoder(), log_level=255, use_thunks=True)
        self.forwarder3 = NFNForwarder(0, encoder=self.get_encoder(), log_level=255, use_thunks=True)
        self.forwarder1_port = self.forwarder1.linklayer.interfaces[0].get_port()
        self.forwarder2_port = self.forwarder2.linklayer.interfaces[0].get_port()
        self.forwarder3_port = self.forwarder3.linklayer.interfaces[0].get_port()

        self.client = Fetch("127.0.0.1", self.forwarder1_port, 255, self.get_encoder())
        self.mgmt1 = MgmtClient(self.forwarder1_port)
        self.mgmt2 = MgmtClient(self.forwarder2_port)
        self.mgmt3 = MgmtClient(self.forwarder3_port)

        self.forwarder1.start_forwarder()
        self.forwarder2.start_forwarder()
        self.forwarder3.start_forwarder()

        self.mgmt1.add_face("127.0.0.1", self.forwarder2_port, 0)
        self.mgmt1.add_face("127.0.0.1", self.forwarder3_port, 0)

        self.mgmt1.add_forwarding_rule(Name("/dat"), [0])
        self.mgmt1.add_forwarding_rule(Name("/fct"), [1])

        self.mgmt2.add_new_content(Name("/dat/data/d1"), "This is our test content object"*20)
        self.mgmt3.add_new_content(Name("/fct/f1"), "PYTHON\nf\ndef f(a):\n    return a.upper()")

    def tearDown(self):
        self.forwarder1.stop_forwarder()
        self.forwarder2.stop_forwarder()
        self.forwarder3.stop_forwarder()
        self.client.stop_fetch()

    def test_simple_thunk_query(self):
        """Test a simple thunk query"""
        name = Name("/fct/f1")
        name += "_(/dat/data/d1)"
        name += "THUNK"
        name += "NFN"
        res = self.client.fetch_data(name, timeout=4)
        self.assertEqual(res, "659")
        #print(self.forwarder1.thunk_layer.planTable.get_plan(self.forwarder1.thunk_layer.removeThunkMarker(name)))

    def test_simple_thunk_query_additional_fwd_rule_to_fct(self):
        """Test a simple thunk query. Add additional rule to have cheap computation at data location"""
        self.mgmt2.add_face("127.0.0.1", self.forwarder3_port, 0)
        self.mgmt2.add_forwarding_rule(Name("/fct"), [0])
        name = Name("/fct/f1")
        name += "_(/dat/data/d1)"
        name += "THUNK"
        name += "NFN"
        res = self.client.fetch_data(name, timeout=4)
        self.assertEqual(res, "39")
        #print(self.forwarder1.thunk_layer.planTable.get_plan(self.forwarder1.thunk_layer.removeThunkMarker(name)))

    def test_simple_thunk_query_additional_fwd_rule_to_data(self):
        """Test a simple thunk query. Add additional rule to have cheap computation at fct location"""
        self.mgmt3.add_face("127.0.0.1", self.forwarder2_port, 0)
        self.mgmt3.add_forwarding_rule(Name("/dat"), [0])
        name = Name("/fct/f1")
        name += "_(/dat/data/d1)"
        name += "THUNK"
        name += "NFN"
        res = self.client.fetch_data(name, timeout=4)
        self.assertEqual(res, "620")
        #print(self.forwarder1.thunk_layer.planTable.get_plan(self.forwarder1.thunk_layer.removeThunkMarker(name)))
