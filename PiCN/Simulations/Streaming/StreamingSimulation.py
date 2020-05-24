"""Simulate a Streaming Scenario.
In this simulation the NFNPythonExecutorStreaming is used. With the use of this Executor we can take advantage of fetch
while compute. So while fetching the next part of the stream the previous part can already be used for the computation.

Scenario consists of two NFN Nodes and a Client.

Client  <--------> NFN0 <------------> NFN1 <-----------> Repo1
"""

import os
import shutil
import unittest
import time

from PiCN.Layers.LinkLayer.Interfaces import SimulationBus
from PiCN.Layers.NFNLayer.NFNExecutor.NFNPythonExecutorStreaming import NFNPythonExecutorStreaming
from PiCN.Layers.PacketEncodingLayer.Encoder import NdnTlvEncoder
from PiCN.Mgmt import MgmtClient
from PiCN.Packets import Name
from PiCN.ProgramLibs.Fetch import Fetch
from PiCN.ProgramLibs.ICNDataRepository import ICNDataRepository
from PiCN.ProgramLibs.NFNForwarder import NFNForwarder


class StreamingSimulation(unittest.TestCase):
    """Simulate a Streaming Scenario."""


    def setUp(self):
        self.simulation_bus = SimulationBus(packetencoder=NdnTlvEncoder())

        self.fetch_tool1 = Fetch("nfn0", None, 255, NdnTlvEncoder(), interfaces=[self.simulation_bus.add_interface("fetchtoo11")])

        self.nfn0 = NFNForwarder(port=0, encoder=NdnTlvEncoder(),
                        interfaces=[self.simulation_bus.add_interface("nfn0")], log_level=255, executors={"PYTHONSTREAM": NFNPythonExecutorStreaming()},
                        ageing_interval=1)

        self.nfn0.executors["PYTHONSTREAM"].initialize_executor(self.nfn0.nfnlayer.queue_to_lower, self.nfn0.nfnlayer.queue_from_lower, self.nfn0.nfnlayer.computation_table, self.nfn0.nfnlayer.cs, self.nfn0.icnlayer.pit)

        self.nfn1 = NFNForwarder(port=0, encoder=NdnTlvEncoder(),
                                interfaces=[self.simulation_bus.add_interface("nfn1")], log_level=255, executors={"PYTHONSTREAM": NFNPythonExecutorStreaming()},
                                ageing_interval=1)

        self.nfn1.executors["PYTHONSTREAM"].initialize_executor(self.nfn1.nfnlayer.queue_to_lower, self.nfn1.nfnlayer.queue_from_lower, self.nfn1.nfnlayer.computation_table, self.nfn1.nfnlayer.cs, self.nfn1.icnlayer.pit)

        self.repo1 = ICNDataRepository("/tmp/repo1", Name("/repo/r1"), 0, 255, NdnTlvEncoder(), False, False,
                                 interfaces=[self.simulation_bus.add_interface("repo1")])

        self.mgmt_client0 = MgmtClient(self.nfn0.mgmt.mgmt_sock.getsockname()[1])
        self.mgmt_client1 = MgmtClient(self.nfn1.mgmt.mgmt_sock.getsockname()[1])


    def tearDown(self):
        self.nfn0.stop_forwarder()
        self.nfn1.stop_forwarder()
        self.repo1.stop_repo()
        self.fetch_tool1.stop_fetch()
        self.simulation_bus.stop_process()
        self.tearDown_repo()

    def setup_faces_and_connections(self):
        self.nfn0.start_forwarder()
        self.nfn1.start_forwarder()

        self.repo1.start_repo()

        self.simulation_bus.start_process()

        time.sleep(3)

        #setup forwarding rules
        self.mgmt_client0.add_face("nfn1", None, 0)
        self.mgmt_client0.add_forwarding_rule(Name("/lib"), [0])

        self.mgmt_client1.add_face("repo1", None, 0)
        self.mgmt_client1.add_forwarding_rule(Name("/repo/r1"), [0])

        #TODO: back connection?
        self.mgmt_client1.add_face("nfn0", None, 0)
        self.mgmt_client1.add_forwarding_rule(Name("/lib"), [1])

        #setup function code

        #multi name
        self.mgmt_client1.add_new_content(Name("/lib/multiname"),
                                     "PYTHONSTREAM\nmultiname\ndef multiname(arg):\n    a = get_next(arg)\n    a = a.upper()\n    b = get_next(arg)\n    b = b.upper()\n    c = get_next(arg)\n    c = c.upper()\n    d = get_next(arg)\n    d = d.upper()\n    e = get_next(arg)\n    e = e.upper()\n    f = get_next(arg)\n    f = f.upper()\n    g = get_next(arg)\n    g = g.upper()\n    h = get_next(arg)\n    h = h.upper()\n    i = get_next(arg)\n    i = i.upper()\n    j = get_next(arg)\n    j = j.upper()\n    return a + b + c + d + e + f + g + h + i + j")

        #single name - two layer
        self.mgmt_client0.add_new_content(Name("/lib/node0"),
                                     "PYTHONSTREAM\ngetnext_on_writeout\ndef getnext_on_writeout(arg):\n    print('Start äussere')\n    a = get_next(arg)\n    a = a.upper()\n    b = get_next(arg)\n    b = b.upper()\n    c = get_next(arg)\n    c = c.upper()\n    d = get_next(arg)\n    d = d.upper()\n    e = get_next(arg)\n    e = e.upper()\n    f = get_next(arg)\n    f = f.upper()\n    g = get_next(arg)\n    g = g.upper()\n    h = get_next(arg)\n    h = h.upper()\n    i = get_next(arg)\n    i = i.upper()\n    j = get_next(arg)\n    j = j.upper()\n    print('Ende äussere')\n    return a + b + c + d + e + f + g + h + i + j")

        self.mgmt_client1.add_new_content(Name("/lib/node1"),
                                     "PYTHONSTREAM\nwriteout_on_getnext\ndef writeout_on_getnext(arg):\n    print('Start innere')\n    a = get_next(arg)\n    write_out(a)\n    a = get_next(arg)\n    write_out(a)\n    a = get_next(arg)\n    write_out(a)\n    a = get_next(arg)\n    write_out(a)\n    a = get_next(arg)\n    write_out(a)\n    a = get_next(arg)\n    write_out(a)\n    a = get_next(arg)\n    write_out(a)\n    a = get_next(arg)\n    write_out(a)\n    a = get_next(arg)\n    write_out(a)\n    a = get_next(arg)\n    write_out(a)\n    last_write_out()\n    return print('Ende innere')")


    def generate_name_files(self, path: str, number: int):
        with open(path + "/name" + str(number), "w") as f:
            f.write("Content of name" + str(number) + ". ")
        f.close()


    def setup_repo(self):
        self.path = "/tmp/repo1"
        try:
            os.stat(self.path)
        except:
            os.mkdir(self.path)
        with open(self.path + "/data1", 'w+') as content_file:
            content_file.write("sdo:\n")
            for i in range(1, 11):
                content_file.write("/repo/r1/name" + str(i) + "\n")
                self.generate_name_files(self.path, i)
            content_file.write("sdo:endstreaming\n")


    def tearDown_repo(self):
        try:
            shutil.rmtree(self.path)
            os.remove("/tmp/repo")
        except:
            pass


    def test_multiname(self):
        """Multiname test with input data from repo"""
        self.setup_repo()
        self.setup_faces_and_connections()

        name = Name("/lib/multiname")
        name += '_(/repo/r1/data1)'
        name += "NFN"

        res = self.fetch_tool1.fetch_data(name, timeout=40)
        print(res)
        self.assertEqual("CONTENT OF NAME1. CONTENT OF NAME2. CONTENT OF NAME3. CONTENT OF NAME4. CONTENT OF NAME5. CONTENT OF NAME6. CONTENT OF NAME7. CONTENT OF NAME8. CONTENT OF NAME9. CONTENT OF NAME10. ", res)


    def test_singlename(self):
        """Singlename test over two layers with input data from repo"""
        self.setup_repo()
        self.setup_faces_and_connections()

        scenario_node_1 = Name("/lib/node1")
        scenario_node_1 += "#(=/repo/r1/data1=)"
        scenario_node_1 += "NFN"

        scenario_node_0 = Name("/lib/node0")
        scenario_node_0 += '_("' + str(scenario_node_1) + '")'
        scenario_node_0 += "NFN"

        res = self.fetch_tool1.fetch_data(scenario_node_0, timeout=40)
        print(res)
        self.assertEqual(
            "CONTENT OF NAME1. CONTENT OF NAME2. CONTENT OF NAME3. CONTENT OF NAME4. CONTENT OF NAME5. CONTENT OF NAME6. CONTENT OF NAME7. CONTENT OF NAME8. CONTENT OF NAME9. CONTENT OF NAME10. ",
            res)
