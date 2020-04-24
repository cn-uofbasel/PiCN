import os

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
nfn_fwd0.executors["PYTHONSTREAM"].initialize_executor(nfn_fwd0.nfnlayer.queue_to_lower, nfn_fwd0.nfnlayer.queue_from_lower, nfn_fwd0.nfnlayer.computation_table, nfn_fwd0.nfnlayer.cs)

nfn_fwd1 = NFNForwarder(port=0, encoder=NdnTlvEncoder(),
                        interfaces=[simulation_bus.add_interface("nfn1")], log_level=255, executors={"PYTHONSTREAM": NFNPythonExecutorStreaming()},
                        ageing_interval=1)
nfn_fwd1.executors["PYTHONSTREAM"].initialize_executor(nfn_fwd1.nfnlayer.queue_to_lower, nfn_fwd1.nfnlayer.queue_from_lower, nfn_fwd1.nfnlayer.computation_table, nfn_fwd1.nfnlayer.cs)

#transform_fwd1 = NFNForwarder(port=0, encoder=NdnTlvEncoder(),
#                        interfaces=[simulation_bus.add_interface("transform1")], log_level=255, executors={"PYTHONSTREAM": NFNPythonExecutorStreaming()},
#                       ageing_interval=1)
#transform_fwd1.executors["PYTHONSTREAM"].initialize_executor(transform_fwd1.nfnlayer.queue_to_lower, transform_fwd1.nfnlayer.queue_from_lower, transform_fwd1.nfnlayer.computation_table, transform_fwd1.nfnlayer.cs)

repo = ICNDataRepository("./InputFiles", Name("/repo/r1"), 0, 255, NdnTlvEncoder(), False, False, interfaces=[simulation_bus.add_interface("repo")])
repo.start_repo()


mgmt_client0 = MgmtClient(nfn_fwd0.mgmt.mgmt_sock.getsockname()[1])
mgmt_client1 = MgmtClient(nfn_fwd1.mgmt.mgmt_sock.getsockname()[1])
#mgmt_client2 = MgmtClient(transform_fwd1.mgmt.mgmt_sock.getsockname()[1])

fetch_tool = Fetch("nfn0", None, 255, NdnTlvEncoder(), interfaces=[simulation_bus.add_interface("fetchtool1")])

nfn_fwd0.start_forwarder()
nfn_fwd1.start_forwarder()
#transform_fwd1.start_forwarder()

simulation_bus.start_process()

mgmt_client0.add_face("nfn1", None, 0)
mgmt_client0.add_forwarding_rule(Name("/repo/r1"), [0])
mgmt_client0.add_forwarding_rule(Name("/lib/node1"), [0])
mgmt_client1.add_face("repo", None, 0)
mgmt_client1.add_forwarding_rule(Name("/repo/r1"), [0])
#mgmt_client1.add_forwarding_rule(Name("/lib"), [0])
#mgmt_client2.add_face("repo", None, 0)
#mgmt_client2.add_forwarding_rule(Name("/repo/r1"), [0])

mgmt_client0.add_new_content(Name("/lib/node0"),"PYTHONSTREAM\ngetnext_on_writeout\ndef getnext_on_writeout(arg):\n    return get_next(arg)")

#mgmt_client1.add_new_content(Name("/lib/node1"),"PYTHONSTREAM\nwriteout_on_getnext\ndef writeout_on_getnext(arg):\n    a = get_next(arg)\n    b = get_next(arg)\n    c = get_next(arg)\n    d = get_next(arg)\n    e = get_next(arg)\n    f = get_next(arg)\n    g = get_next(arg)\n    h = get_next(arg)\n    i = get_next(arg)\n    j = get_next(arg)\n    write_out(a)\n    write_out(b)\n    write_out(c)\n    write_out(d)\n    write_out(e)\n    write_out(f)\n    write_out(g)\n    write_out(h)\n    write_out(i)\n    write_out(j)\n    last_write_out()")

mgmt_client1.add_new_content(Name("/lib/node1"),"PYTHONSTREAM\nwriteout_on_getnext\ndef writeout_on_getnext(arg):\n    a = get_next(arg)\n    write_out(a)\n    a = get_next(arg)\n    write_out(a)\n    a = get_next(arg)\n    write_out(a)\n    a = get_next(arg)\n    write_out(a)\n    a = get_next(arg)\n    write_out(a)\n    a = get_next(arg)\n    write_out(a)\n    a = get_next(arg)\n    write_out(a)\n    a = get_next(arg)\n    write_out(a)\n    a = get_next(arg)\n    write_out(a)\n    a = get_next(arg)\n    write_out(a)\n    last_write_out()")

scenario_node_1 = Name("/lib/node1")
scenario_node_1 += "#(=/repo/r1/exampleInputFile=)"
scenario_node_1 += "NFN"

# res1 = fetch_tool.fetch_data(scenario_node_1)
# print("Interest result: ", res1)
# print("\n")

scenario_node_0 = Name("/lib/node0")
scenario_node_0 += '_("' + str(scenario_node_1) + '")'
scenario_node_0 += "NFN"

print("The computation", scenario_node_0)
res = fetch_tool.fetch_data(scenario_node_0)
print("Interest result: ", res)


nfn_fwd0.stop_forwarder()
nfn_fwd1.stop_forwarder()
#transform_fwd1.stop_forwarder()
repo.stop_repo()
fetch_tool.stop_fetch()
simulation_bus.stop_process()
mgmt_client0.shutdown()
mgmt_client1.shutdown()

#mgmt_client2.shutdown()
