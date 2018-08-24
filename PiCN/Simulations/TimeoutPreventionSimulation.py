"""Simulate a Scenario where timeout prevention is required.

Scenario consists of two NFN nodes and a Client. Goal of the simulation is to add en

Client <--------> NFN1 <-----------> NFN2
"""

import abc
import queue
import unittest
import os
import time

from PiCN.Layers.LinkLayer.Interfaces import SimulationBus
from PiCN.Layers.LinkLayer.Interfaces import AddressInfo
from PiCN.Layers.NFNLayer.NFNOptimizer import ToDataFirstOptimizer
from PiCN.ProgramLibs.ICNForwarder import ICNForwarder
from PiCN.ProgramLibs.Fetch import Fetch
from PiCN.ProgramLibs.NFNForwarder import NFNForwarder
from PiCN.ProgramLibs.ICNDataRepository import ICNDataRepository
from PiCN.Layers.PacketEncodingLayer.Encoder import BasicEncoder, SimpleStringEncoder, NdnTlvEncoder
from PiCN.Packets import Content, Interest, Name
from PiCN.Mgmt import MgmtClient


class TimeoutPreventionSimulation(unittest.TestCase):
    """Simulate a Scenario where timeout prevention is required"""

    @abc.abstractmethod
    def get_encoder(self) -> BasicEncoder:
        return SimpleStringEncoder

    def setUp(self):
        self.encoder_type = self.get_encoder()
        self.simulation_bus = SimulationBus(packetencoder=self.encoder_type())

        self.fetch_tool1 = Fetch("nfn1", None, 255, self.encoder_type(), interfaces=[self.simulation_bus.add_interface("fetchtool1")])

        self.nfn1 = NFNForwarder(port=0, encoder=self.encoder_type(),
                                 interfaces=[self.simulation_bus.add_interface("nfn1")], log_level=255, ageing_interval=1)
        self.nfn2 = NFNForwarder(port=0, encoder=self.encoder_type(),
                                 interfaces=[self.simulation_bus.add_interface("nfn2")], log_level=255, ageing_interval=1)


        self.nfn1.icnlayer.pit.set_pit_timeout(0)
        self.nfn1.icnlayer.cs.set_cs_timeout(30)
        self.nfn2.icnlayer.pit.set_pit_timeout(0)
        self.nfn2.icnlayer.cs.set_cs_timeout(30)

        self.nfn1.nfnlayer.optimizer = ToDataFirstOptimizer(self.nfn1.icnlayer.cs, self.nfn1.icnlayer.fib, self.nfn1.icnlayer.pit, self.nfn1.linklayer.faceidtable)
        self.nfn2.nfnlayer.optimizer = ToDataFirstOptimizer(self.nfn2.icnlayer.cs, self.nfn2.icnlayer.fib, self.nfn2.icnlayer.pit, self.nfn2.linklayer.faceidtable)

        self.mgmt_client1 = MgmtClient(self.nfn1.mgmt.mgmt_sock.getsockname()[1])
        self.mgmt_client2 = MgmtClient(self.nfn2.mgmt.mgmt_sock.getsockname()[1])

    def tearDown(self):
        self.nfn1.stop_forwarder()
        self.nfn2.stop_forwarder()
        self.fetch_tool1.stop_fetch()
        self.simulation_bus.stop_process()

    def setup_faces_and_connections(self):
        self.nfn1.start_forwarder()
        self.nfn2.start_forwarder()

        self.simulation_bus.start_process()

        # setup nfn1
        self.mgmt_client1.add_face("nfn2", None, 0)
        self.mgmt_client1.add_forwarding_rule(Name("/lib"), [0])
        self.mgmt_client1.add_new_content(Name("/test/data/string"), "This is a String")

        # setup nfn2
        self.mgmt_client1.add_face("nfn1", None, 0)
        self.mgmt_client1.add_forwarding_rule(Name("/test"), [0])
        self.mgmt_client2.add_new_content(Name("/lib/func/f1"),
                                          "PYTHON\nf\ndef f(a):\n    for i in range(0,100000000):\n        a.upper()\n    return a.upper() + ' WITHOUT TIMEOUT'")


    def test_simple_timeout_prevention(self):
        """Simple test to see if timeout prevention works"""
        self.setup_faces_and_connections()

        name = Name("/lib/func/f1")
        name += '_("helloworld")'
        name += "NFN"

        res = self.fetch_tool1.fetch_data(name, timeout=0)
        time.sleep(3)
        self.assertEqual("HELLOWORLD WITHOUT TIMEOUT", res)
        print(res)

    def test_timeout_prevention_if_no_comp(self):
        """Simple test to see if timeout prevention works if no computation is available"""
        self.setup_faces_and_connections()

        name = Name("/lib/func/f2")
        name += '_("helloworld")'
        name += "NFN"

        res = self.fetch_tool1.fetch_data(name, timeout=0)
        self.assertEqual("Received Nack: no forwarding rule", res)
        time.sleep(3)
        print(res)
