"""Simulate a simple Edge Computing Scenario

Scenario consists of three Road Side Units (RSU) which are basically edge computing nodes.
The client is free to move between the RSUs.

RSU1 -------- RSU2 -----------RSU3

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

        self.fetch_tool = Fetch("icnfwd1", None, 255, self.encoder_type(), [self.simulation_bus.add_interface("fetchtool")])

        self.rsu1 = NFNForwarder(port=0, encoder=self.encoder_type(),
                                           interfaces=[self.simulation_bus.add_interface("icnfwd1")], log_level=255)
        self.rsu2 = NFNForwarder(port=0, encoder=self.encoder_type(),
                                           interfaces=[self.simulation_bus.add_interface("icnfwd2")], log_level=255)

        self.rsu3 = NFNForwarder(port=0, encoder=self.encoder_type(),
                                 interfaces=[self.simulation_bus.add_interface("icnfwd2")], log_level=255)

    def tearDown(self):
        pass

    def setup_faces_and_connections(self):
        pass
    #TODO

    def test_without_data_from_client(self):
        pass