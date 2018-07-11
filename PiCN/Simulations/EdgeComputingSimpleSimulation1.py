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

        self.fetch_tool = Fetch("rsu1", None, 255, self.encoder_type(), [self.simulation_bus.add_interface("fetchtool")])

        self.rsu1 = NFNForwarder(port=0, encoder=self.encoder_type(),
                                 interfaces=[self.simulation_bus.add_interface("rsu1")], log_level=255)

        self.rsu2 = NFNForwarder(port=0, encoder=self.encoder_type(),
                                 interfaces=[self.simulation_bus.add_interface("rsu2")], log_level=255)
        self.rsu3 = NFNForwarder(port=0, encoder=self.encoder_type(),
                                 interfaces=[self.simulation_bus.add_interface("rsu3")], log_level=255)

        self.mgmt_client1 = MgmtClient(self.rsu1.mgmt.mgmt_sock.getsockname()[1])
        self.mgmt_client2 = MgmtClient(self.rsu2.mgmt.mgmt_sock.getsockname()[1])
        self.mgmt_client3 = MgmtClient(self.rsu3.mgmt.mgmt_sock.getsockname()[1])

    def tearDown(self):
        self.rsu1.stop_forwarder()
        self.rsu2.stop_forwarder()
        self.rsu2.stop_forwarder()
        self.simulation_bus.stop_process()
        self.fetch_tool.stop_fetch()
        self.mgmt_client1.shutdown()
        self.mgmt_client2.shutdown()
        self.mgmt_client3.shutdown()

    def setup_faces_and_connections(self):
        self.rsu1.start_forwarder()
        self.rsu2.start_forwarder()
        self.rsu3.start_forwarder()

        self.simulation_bus.start_process()

        #setup rsu1

        self.mgmt_client1.add_face("rsu2", None, 0)
        #mgmt_client1.add_forwarding_rule(Name("/rsu"), 0)
        self.mgmt_client1.add_new_content(Name("/rsu/func/f1"), "PYTHON\nf\ndef f(a):\n    for i in range(0,50000000):\n        a.upper()\n    return a.upper()")

        #setup rsu2

        self.mgmt_client2.add_face("rsu1", None, 0)
        self.mgmt_client2.add_face("rsu3", None, 0)
        self.mgmt_client2.add_forwarding_rule(Name("/rsu"), 0)
        self.mgmt_client2.add_forwarding_rule(Name("/rsu"), 1)
        self.mgmt_client2.add_new_content(Name("/rsu/func/f1"), "PYTHON\nf\ndef f(a):\n    for i in range(0,50000000):\n        a.upper()\n    return a.upper()")

        #setup rsu3
        self.mgmt_client3.add_face("rsu2", None, 0)
        self.mgmt_client3.add_forwarding_rule(Name("/rsu"), 0)
        self.mgmt_client3.add_new_content(Name("/rsu/func/f1"), "PYTHON\nf\ndef f(a):\n    for i in range(0,50000000):\n        a.upper()\n    return a.upper()")


    def test_without_data_from_client(self):

        self.setup_faces_and_connections()

        name = Name("/rsu/func/f1")
        name += '_("helloworld")'
        name += "NFN"
        computation_name = Name("/func/f1")

        res = self.fetch_tool.fetch_data(name, timeout=10)
        print(res)
        self.assertEqual(res, "HELLOWORLD")



