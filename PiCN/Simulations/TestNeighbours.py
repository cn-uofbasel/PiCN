"""Simulate a simple Data Offloading Scenario

Scenario consists of three Road Side Units (RSU) and a Client moving around freely.

RSU1 <--------> RSU2 <-----------> RSU3

        client ->

Test1
The client sends an interest to RSU1 which involves data that is stored on the client itself.
The RSU1 sends an interest and the data is uploaded to RSU1

Test2
While uploading the connection is interrupted. The client connects to the next RSU and the upload continues.


"""
import unittest
from time import sleep

from PiCN.Layers.ChunkLayer.Chunkifyer import SimpleContentChunkifyer
from PiCN.Layers.LinkLayer.Interfaces import SimulationBus
from PiCN.Layers.NFNLayer.NFNOptimizer import EdgeComputingOptimizer
from PiCN.Layers.PacketEncodingLayer.Encoder import SimpleStringEncoder
from PiCN.Mgmt import MgmtClient
from PiCN.Packets import Name, Content
from PiCN.ProgramLibs.Fetch import Fetch
from PiCN.ProgramLibs.ICNForwarder import ICNForwarder
from PiCN.ProgramLibs.NFNForwarder.NFNForwarderData import NFNForwarderData


class TestNeighbours(unittest.TestCase):
    """run the simple Data Offloading Scenario Simulation"""

    def setUp(self):
        self.encoder_type = SimpleStringEncoder()
        self.simulation_bus = SimulationBus(packetencoder=self.encoder_type)
        chunk_size = 4
        self.chunkifyer = SimpleContentChunkifyer(chunk_size)

        self.car = ICNForwarder(0, encoder=self.encoder_type, routing=True,
                                interfaces=[self.simulation_bus.add_interface("car")])
        self.fetch_tool_car = Fetch("car", None, 255, self.encoder_type,
                                    interfaces=[self.simulation_bus.add_interface("ftcar")])
        self.mgmt_client_car = MgmtClient(self.car.mgmt.mgmt_sock.getsockname()[1])

        self.rsus = []
        self.fetch_tools = []
        self.mgmt_clients = []

        for i in range(4):
            self.rsus.append(NFNForwarderData(0, encoder=self.encoder_type,
                                              interfaces=[self.simulation_bus.add_interface(f"rsu{i}")],
                                              chunk_size=chunk_size, num_of_forwards=0))
            self.fetch_tools.append(Fetch(f"rsu{i}", None, 255, self.encoder_type,
                                          interfaces=[self.simulation_bus.add_interface(f"ft{i}")]))
            self.rsus[i].nfnlayer.optimizer = EdgeComputingOptimizer(self.rsus[i].icnlayer.cs,
                                                                     self.rsus[i].icnlayer.fib,
                                                                     self.rsus[i].icnlayer.pit,
                                                                     self.rsus[i].linklayer.faceidtable)
            self.mgmt_clients.append(MgmtClient(self.rsus[i].mgmt.mgmt_sock.getsockname()[1]))

    def tearDown(self):
        self.car.stop_forwarder()
        self.fetch_tool_car.stop_fetch()

        for rsu in self.rsus:
            rsu.stop_forwarder()

        for fetch_tool in self.fetch_tools:
            fetch_tool.stop_fetch()

        self.simulation_bus.stop_process()

    def setup_faces_and_connections(self):
        self.car.start_forwarder()

        for rsu in self.rsus:
            rsu.start_forwarder()

        self.simulation_bus.start_process()

        # setup rsu0
        self.mgmt_clients[0].add_face("car", None, 0)
        self.mgmt_clients[0].add_face("rsu1", None, 0)
        self.mgmt_clients[0].add_forwarding_rule(Name("/car"), [0])
        self.mgmt_clients[0].add_forwarding_rule(Name("/nR"), [1])
        self.mgmt_clients[0].add_new_content(Name("/rsu/func/f1"), "PYTHON\nf\ndef f(a):\n return a + ' World'")

        # setup rsu1
        self.mgmt_clients[1].add_face("car", None, 0)
        self.mgmt_clients[1].add_face("rsu0", None, 0)
        self.mgmt_clients[1].add_face("rsu2", None, 0)
        self.mgmt_clients[1].add_forwarding_rule(Name("/car"), [0])
        self.mgmt_clients[1].add_forwarding_rule(Name("/nL"), [1])
        self.mgmt_clients[1].add_forwarding_rule(Name("/nR"), [2])
        self.mgmt_clients[1].add_new_content(Name("/rsu/func/f1"), "PYTHON\nf\ndef f(a):\n return a + ' World'")

        # setup rsu2
        self.mgmt_clients[2].add_face("car", None, 0)
        self.mgmt_clients[2].add_face("rsu1", None, 0)
        self.mgmt_clients[2].add_face("rsu3", None, 0)
        self.mgmt_clients[2].add_forwarding_rule(Name("/car"), [0])
        self.mgmt_clients[2].add_forwarding_rule(Name("/nL"), [1])
        self.mgmt_clients[2].add_forwarding_rule(Name("/nR"), [2])
        self.mgmt_clients[2].add_new_content(Name("/rsu/func/f1"), "PYTHON\nf\ndef f(a):\n return a + ' World'")

        # setup rsu3
        self.mgmt_clients[3].add_face("car", None, 0)
        self.mgmt_clients[3].add_face("rsu2", None, 0)
        self.mgmt_clients[3].add_forwarding_rule(Name("/car"), [0])
        self.mgmt_clients[3].add_forwarding_rule(Name("/nL"), [1])
        self.mgmt_clients[3].add_new_content(Name("/rsu/func/f1"), "PYTHON\nf\ndef f(a):\n return a + ' World'")

        # setup car
        self.mgmt_client_car.add_face("rsu0", None, 0)
        self.mgmt_client_car.add_face("rsu1", None, 0)
        self.mgmt_client_car.add_face("rsu2", None, 0)
        self.mgmt_client_car.add_forwarding_rule(Name("/rsu"), [0])

        self.d = Content(Name("/car/data/test1"), "Test" * 10)
        self.meta_data, self.data = self.chunkifyer.chunk_data(self.d)

        for md in self.meta_data:
            self.car.icnlayer.cs.add_content_object(md)

        # only load n-2 chunks to car to simulate car getting out of each while uploading
        for d in self.data[:5]:
            self.mgmt_client_car.add_new_content(d.name, d.content)



    def test_nfn_interest(self):
        self.setup_faces_and_connections()

        name = Name("/rsu/func/f1")
        name += '_(/car/data/test1)'
        name += "NFN"

        res = self.fetch_tools[0].fetch_data(name)
        print(res)

        sleep(1)
        print("\n" * 20 + "RSU 2 STARTING")

        for d in self.data[5:-2]:
            self.mgmt_client_car.add_new_content(d.name, d.content)
        for d in self.data[:5]:
            self.car.icnlayer.cs.remove_content_object(d.name)
        for md in self.meta_data:
            self.car.icnlayer.cs.remove_content_object(md.name)

        res2 = self.fetch_tools[1].fetch_data(name, 30)
        print(res2)

        sleep(1)
        print("\n" * 20 + "RSU 3 STARTING")

        for d in self.data[-2:]:
            self.mgmt_client_car.add_new_content(d.name, d.content)
        for d in self.data[:-2]:
            self.car.icnlayer.cs.remove_content_object(d.name)

        res3 = self.fetch_tools[2].fetch_data(name)
        print(res3)
        self.assertEqual(self.d.content + " World", res3)
