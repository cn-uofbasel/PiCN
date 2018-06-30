"""Test the PiCN Simulation System"""

import unittest

from PiCN.Layers.LinkLayer.Interfaces import SimulationBus
from PiCN.Layers.LinkLayer.Interfaces import SimulationInterface
from PiCN.Layers.LinkLayer.Interfaces import AddressInfo
from PiCN.ProgramLibs.ICNForwarder import ICNForwarder
from PiCN.ProgramLibs.Fetch import Fetch
from PiCN.Layers.PacketEncodingLayer.Encoder import SimpleStringEncoder
from PiCN.Packets import Content, Interest, Name
from PiCN.Mgmt import MgmtClient

class test_Simulation(unittest.TestCase):
    """Test the PiCN Simulation System"""

    def setUp(self):
        self.simulation_bus = SimulationBus({})

        self.fetchiface = self.simulation_bus.add_interface("fetch")
        self.encoder = SimpleStringEncoder()
        self.icn_forwarder1 = ICNForwarder(port=0, interfaces=[self.simulation_bus.add_interface("icnfwd1")])
        self.icn_forwarder2 = ICNForwarder(port=0, interfaces=[self.simulation_bus.add_interface("icnfwd2")])

        self.simulation_bus.start_process()

    def tearDown(self):
        self.simulation_bus.stop_process()
        self.icn_forwarder1.stop_forwarder()
        self.icn_forwarder2.stop_forwarder()

    def test_send_single_packet(self):
        """Test fetching a single content object over the simulation bus"""
        self.icn_forwarder1.start_forwarder()
        self.icn_forwarder2.start_forwarder()

        fid1 = self.icn_forwarder1.linklayer.faceidtable.get_or_create_faceid(AddressInfo("icnfwd2", 0))
        self.icn_forwarder1.icnlayer.fib.add_fib_entry(Name("/test"), fid1)

        self.icn_forwarder2.icnlayer.cs.add_content_object(Content("/test/data", "HelloWorld"), static=True)

        interest = Interest("/test/data")
        wire_data = self.encoder.encode(interest)
        self.fetchiface.send(wire_data, "icnfwd1")

        res, src = self.fetchiface.receive()
        self.assertEqual(src, "icnfwd1")
        c = self.encoder.decode(res)
        self.assertEqual(c, Content("/test/data", "HelloWorld"))
