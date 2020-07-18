import os
import time
from PiCN.Layers.NFNLayer.NFNExecutor.NFNPythonExecutorStreaming import NFNPythonExecutorStreaming
from PiCN.ProgramLibs.Fetch import Fetch
from PiCN.ProgramLibs.ICNDataRepository import ICNDataRepository
from PiCN.ProgramLibs.NFNForwarder import NFNForwarder
from PiCN.Layers.LinkLayer.Interfaces import SimulationBus
from PiCN.Layers.PacketEncodingLayer.Encoder import NdnTlvEncoder
from PiCN.Mgmt import MgmtClient
from PiCN.Packets import Name

simulation_bus = SimulationBus(packetencoder=NdnTlvEncoder())

nfn_fwd0 = NFNForwarder(port=0, encoder=NdnTlvEncoder(),
                        interfaces=[simulation_bus.add_interface("nfn0")], log_level=255, executors={"PYTHONSTREAM": NFNPythonExecutorStreaming()},
                        ageing_interval=1)
nfn_fwd0.executors["PYTHONSTREAM"].initialize_executor(nfn_fwd0.nfnlayer.queue_to_lower, nfn_fwd0.nfnlayer.queue_from_lower, nfn_fwd0.nfnlayer.cs, False)
nfn_fwd0.icnlayer.pit.ageing = lambda x : "return"

nfn_fwd1 = NFNForwarder(port=0, encoder=NdnTlvEncoder(),
                        interfaces=[simulation_bus.add_interface("nfn1")], log_level=255, executors={"PYTHONSTREAM": NFNPythonExecutorStreaming()},
                        ageing_interval=1)
nfn_fwd1.executors["PYTHONSTREAM"].initialize_executor(nfn_fwd1.nfnlayer.queue_to_lower, nfn_fwd1.nfnlayer.queue_from_lower, nfn_fwd1.nfnlayer.cs, False)
nfn_fwd1.icnlayer.pit.ageing = lambda x : "return"

repo = ICNDataRepository("./InputFiles", Name("/repo/r1"), 0, 255, NdnTlvEncoder(), False, False, interfaces=[simulation_bus.add_interface("repo")])
repo.start_repo()

mgmt_client0 = MgmtClient(nfn_fwd0.mgmt.mgmt_sock.getsockname()[1])
mgmt_client1 = MgmtClient(nfn_fwd1.mgmt.mgmt_sock.getsockname()[1])

fetch_tool = Fetch("nfn0", None, 255, NdnTlvEncoder(), interfaces=[simulation_bus.add_interface("fetchtoo1")])

nfn_fwd0.start_forwarder()
nfn_fwd1.start_forwarder()

simulation_bus.start_process()

mgmt_client0.add_face("nfn1", None, 0)
mgmt_client0.add_forwarding_rule(Name("/repo/r1"), [0])
mgmt_client0.add_forwarding_rule(Name("/lib"), [0])
mgmt_client1.add_face("repo", None, 0)
mgmt_client1.add_forwarding_rule(Name("/repo/r1"), [0])

mgmt_client0.add_new_content(Name("/lib/node0"),"PYTHONSTREAM\ngetnext_on_writeout\ndef getnext_on_writeout(arg):\n    print('Start äussere')\n    a = get_next(arg)\n    sleep(2)\n    b = get_next(arg)\n    sleep(2)\n    c = get_next(arg)\n    sleep(2)\n    d = get_next(arg)\n    sleep(2)\n    e = get_next(arg)\n    sleep(2)\n    f = get_next(arg)\n    sleep(2)\n    g = get_next(arg)\n    sleep(2)\n    h = get_next(arg)\n    sleep(2)\n    i = get_next(arg)\n    sleep(2)\n    j = get_next(arg)\n    sleep(2)\n    print('Ende äussere')\n    return a + b + c + d + e + f + g + h + i + j")

mgmt_client1.add_new_content(Name("/lib/node1"),"PYTHONSTREAM\nwriteout_on_getnext\ndef writeout_on_getnext(arg):\n    print('Start innere')\n    write_out_on_get_next(arg)\n    return print('Ende innere')\n")


scenario_node_1 = Name("/lib/node1")
scenario_node_1 += "#(=/repo/r1/exampleInputFile=)"
scenario_node_1 += "NFN"

scenario_node_0 = Name("/lib/node0")
scenario_node_0 += '_("' + str(scenario_node_1) + '")'
scenario_node_0 += "NFN"



start_time = time.perf_counter()
res = fetch_tool.fetch_data(scenario_node_0, timeout=60)
end_time = time.perf_counter()
print("Interest result:", res)
print("Time needed in seconds:", end_time-start_time)


nfn_fwd0.stop_forwarder()
nfn_fwd1.stop_forwarder()
repo.stop_repo()
fetch_tool.stop_fetch()
simulation_bus.stop_process()
mgmt_client0.shutdown()
mgmt_client1.shutdown()
