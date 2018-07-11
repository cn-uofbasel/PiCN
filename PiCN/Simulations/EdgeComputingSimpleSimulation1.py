"""Simulate a simple Edge Computing Scenario

Scenario consists of three Road Side Units (RSU) which are basically edge computing nodes.
The client is free to move between the RSUs.

RSU1 <--------> RSU2 <-----------> RSU3

        client ->


"""

import abc
import queue
import unittest
import os

from PiCN.Layers.LinkLayer.Interfaces import SimulationBus
from PiCN.Layers.LinkLayer.Interfaces import AddressInfo
from PiCN.Layers.NFNLayer.NFNOptimizer import EdgeComputingOptimizer
from PiCN.ProgramLibs.ICNForwarder import ICNForwarder
from PiCN.ProgramLibs.Fetch import Fetch
from PiCN.ProgramLibs.NFNForwarder import NFNForwarder
from PiCN.ProgramLibs.ICNDataRepository import ICNDataRepository
from PiCN.Layers.PacketEncodingLayer.Encoder import BasicEncoder, SimpleStringEncoder, NdnTlvEncoder
from PiCN.Packets import Content, Interest, Name
from PiCN.Mgmt import MgmtClient


class EdgeComputingSimpleSimulation1(unittest.TestCase):
    """run the simple Edge Computing Scenario Simulation"""

    @abc.abstractmethod
    def get_encoder(self) -> BasicEncoder:
        return SimpleStringEncoder

    def setUp(self):
        self.encoder_type = self.get_encoder()
        self.simulation_bus = SimulationBus(packetencoder=self.encoder_type())

        self.fetch_tool1 = Fetch("rsu1", None, 255, self.encoder_type(), [self.simulation_bus.add_interface("fetchtool1")])
        self.fetch_tool2 = Fetch("rsu2", None, 255, self.encoder_type(), [self.simulation_bus.add_interface("fetchtool2")])

        self.rsu1 = NFNForwarder(port=0, encoder=self.encoder_type(),
                                 interfaces=[self.simulation_bus.add_interface("rsu1")], log_level=255)

        self.rsu2 = NFNForwarder(port=0, encoder=self.encoder_type(),
                                 interfaces=[self.simulation_bus.add_interface("rsu2")], log_level=255)
        self.rsu3 = NFNForwarder(port=0, encoder=self.encoder_type(),
                                 interfaces=[self.simulation_bus.add_interface("rsu3")], log_level=255)


        self.rsu1.nfnlayer.optimizer = EdgeComputingOptimizer(self.rsu1.icnlayer.cs, self.rsu1.icnlayer.fib, self.rsu1.icnlayer.pit)
        self.rsu2.nfnlayer.optimizer = EdgeComputingOptimizer(self.rsu2.icnlayer.cs, self.rsu2.icnlayer.fib, self.rsu2.icnlayer.pit)
        self.rsu3.nfnlayer.optimizer = EdgeComputingOptimizer(self.rsu3.icnlayer.cs, self.rsu3.icnlayer.fib, self.rsu3.icnlayer.pit)

        self.mgmt_client1 = MgmtClient(self.rsu1.mgmt.mgmt_sock.getsockname()[1])
        self.mgmt_client2 = MgmtClient(self.rsu2.mgmt.mgmt_sock.getsockname()[1])
        self.mgmt_client3 = MgmtClient(self.rsu3.mgmt.mgmt_sock.getsockname()[1])

    def tearDown(self):
        self.rsu1.stop_forwarder()
        self.rsu2.stop_forwarder()
        self.rsu3.stop_forwarder()
        self.fetch_tool1.stop_fetch()
        self.fetch_tool2.stop_fetch()
        self.simulation_bus.stop_process()

    def setup_faces_and_connections(self):
        self.rsu1.start_forwarder()
        self.rsu2.start_forwarder()
        self.rsu3.start_forwarder()

        self.simulation_bus.start_process()

        #setup rsu1

        self.mgmt_client1.add_face("rsu2", None, 0)
        self.mgmt_client1.add_forwarding_rule(Name("/rsu"), 0)
        self.mgmt_client1.add_new_content(Name("/rsu/func/f1"), "PYTHON\nf\ndef f(a):\n    for i in range(0,50000000):\n        a.upper()\n    return a.upper() + ' RSU1'")

        #setup rsu2
        self.mgmt_client2.add_face("rsu1", None, 0)
        self.mgmt_client2.add_face("rsu3", None, 0)
        self.mgmt_client2.add_forwarding_rule(Name("/rsu"), 0)
        self.mgmt_client2.add_forwarding_rule(Name("/rsu"), 1)
        self.mgmt_client2.add_new_content(Name("/rsu/func/f1"), "PYTHON\nf\ndef f(a):\n    for i in range(0,60000000):\n        a.upper()\n    return a.upper() + ' RSU2'")

        #setup rsu3
        self.mgmt_client3.add_face("rsu2", None, 0)
        self.mgmt_client3.add_forwarding_rule(Name("/rsu"), 0)
        self.mgmt_client3.add_new_content(Name("/rsu/func/f1"), "PYTHON\nf\ndef f(a):\n    for i in range(0,50000000):\n        a.upper()\n    return a.upper() + ' RSU3'")


    def test_without_data_from_client(self):

        self.setup_faces_and_connections()

        name = Name("/rsu/func/f1")
        name += '_("helloworld")'
        name += "NFN"
        computation_name = Name("/func/f1")

        res = self.fetch_tool1.fetch_data(name, timeout=10)
        self.assertEqual(res, "HELLOWORLD RSU1")
        print("Result at RSU1:", res)
        res = self.fetch_tool2.fetch_data(name, timeout=10)
        print("Result as fetched from RSU2:", res)
        self.assertEqual(res, "HELLOWORLD RSU2") #since node 2 starts computation too, result is on 2 the one of 2

