"""Test the PiCN Simulation System"""

import multiprocessing
import queue
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

        #self.simulation_bus.start_process()

    def tearDown(self):
        self.simulation_bus.stop_process()
        self.icn_forwarder1.stop_forwarder()
        self.icn_forwarder2.stop_forwarder()

    def test_send_single_packet(self):
        """Test fetching a single content object over the simulation bus"""
        self.icn_forwarder1.start_forwarder()
        self.icn_forwarder2.start_forwarder()
        self.simulation_bus.start_process()

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

    def test_send_single_packet_with_delay(self):
        """Test fetching a single content object over the simulation bus"""

        delay_func = lambda packet: 0.5

        self.fetchiface = self.simulation_bus.add_interface("fetch", delay_func=delay_func)
        self.icn_forwarder1 = ICNForwarder(port=0, interfaces=[self.simulation_bus.add_interface("icnfwd1",
                                                                                                 delay_func=delay_func)])
        self.icn_forwarder2 = ICNForwarder(port=0, interfaces=[self.simulation_bus.add_interface("icnfwd2",
                                                                                                 delay_func=delay_func)])
        self.simulation_bus.start_process()

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

    def test_send_single_packet_with_packet_loss(self):
        """Test fetching a single content object over the simulation bus"""

        packet_loss_func = lambda packet: True

        self.fetchiface = self.simulation_bus.add_interface("fetch", packet_loss_func=packet_loss_func)
        self.icn_forwarder1 = ICNForwarder(port=0, interfaces=[self.simulation_bus.add_interface("icnfwd1",
                                                                                                 packet_loss_func=packet_loss_func)])
        self.icn_forwarder2 = ICNForwarder(port=0, interfaces=[self.simulation_bus.add_interface("icnfwd2",
                                                                                                 packet_loss_func=packet_loss_func)])
        self.simulation_bus.start_process()

        self.icn_forwarder1.start_forwarder()
        self.icn_forwarder2.start_forwarder()

        fid1 = self.icn_forwarder1.linklayer.faceidtable.get_or_create_faceid(AddressInfo("icnfwd2", 0))
        self.icn_forwarder1.icnlayer.fib.add_fib_entry(Name("/test"), fid1)

        self.icn_forwarder2.icnlayer.cs.add_content_object(Content("/test/data", "HelloWorld"), static=True)

        interest = Interest("/test/data")
        wire_data = self.encoder.encode(interest)
        self.fetchiface.send(wire_data, "icnfwd1")
        try:
            self.fetchiface.receive(timeout=4)
        except queue.Empty:
            pass
        else:
            self.fail()
