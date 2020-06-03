import matplotlib.pyplot as plt
import numpy as np

from datetime import datetime

import time
from PiCN.Layers.NFNLayer.NFNExecutor.NFNPythonExecutorStreaming import NFNPythonExecutorStreaming
from PiCN.ProgramLibs.Fetch import Fetch
from PiCN.ProgramLibs.ICNDataRepository import ICNDataRepository
from PiCN.ProgramLibs.NFNForwarder import NFNForwarder
from PiCN.Layers.LinkLayer.Interfaces import SimulationBus
from PiCN.Layers.PacketEncodingLayer.Encoder import NdnTlvEncoder
from PiCN.Mgmt import MgmtClient
from PiCN.Packets import Name

def pathDetection(fileName:str):
    pathList = fileName.split("/")
    path = ""
    for j in range(0, len(pathList) - 1):
        if j is 0:
            path = path + pathList[j]
        else:
            path = path + "/" + pathList[j]
    return path + "/"

def generateNameFiles(path: str, number:int):
    with open(path + "name" + str(number), "w") as f:
        f.write("Inhalt von name" + str(number) + ". ")
    f.close()

def generateExampleFiles(fileName: str, numberOfLines: int):
    path = pathDetection(fileName)
    with open(fileName, "w") as f:
        f.write("sdo:\n")
        for i in range(1, numberOfLines + 1):
            f.write("/repo/r1/name" + str(i) + "\n")
            generateNameFiles(path, i)
        f.write("sdo:endstreaming\n")
    f.close()

classic = False

generateExampleFiles("InputFiles/exampleInputFile", 10)

simulation_bus = SimulationBus(packetencoder=NdnTlvEncoder())

nfn_fwd0 = NFNForwarder(port=0, encoder=NdnTlvEncoder(),
                        interfaces=[simulation_bus.add_interface("nfn0")], log_level=255, executors={"PYTHONSTREAM": NFNPythonExecutorStreaming()},
                        ageing_interval=1)
nfn_fwd0.executors["PYTHONSTREAM"].initialize_executor(nfn_fwd0.nfnlayer.queue_to_lower, nfn_fwd0.nfnlayer.queue_from_lower, nfn_fwd0.nfnlayer.computation_table, nfn_fwd0.nfnlayer.cs, nfn_fwd0.icnlayer.pit, classic)



nfn_fwd1 = NFNForwarder(port=0, encoder=NdnTlvEncoder(),
                        interfaces=[simulation_bus.add_interface("nfn1")], log_level=255, executors={"PYTHONSTREAM": NFNPythonExecutorStreaming()},
                        ageing_interval=1)
nfn_fwd1.executors["PYTHONSTREAM"].initialize_executor(nfn_fwd1.nfnlayer.queue_to_lower, nfn_fwd1.nfnlayer.queue_from_lower, nfn_fwd1.nfnlayer.computation_table, nfn_fwd1.nfnlayer.cs, nfn_fwd1.icnlayer.pit, classic)

nfn_fwd2 = NFNForwarder(port=0, encoder=NdnTlvEncoder(),
                        interfaces=[simulation_bus.add_interface("nfn2")], log_level=255, executors={"PYTHONSTREAM": NFNPythonExecutorStreaming()},
                        ageing_interval=1)
nfn_fwd2.executors["PYTHONSTREAM"].initialize_executor(nfn_fwd2.nfnlayer.queue_to_lower, nfn_fwd2.nfnlayer.queue_from_lower, nfn_fwd2.nfnlayer.computation_table, nfn_fwd2.nfnlayer.cs, nfn_fwd2.icnlayer.pit, classic)

nfn_fwd3 = NFNForwarder(port=0, encoder=NdnTlvEncoder(),
                        interfaces=[simulation_bus.add_interface("nfn3")], log_level=255, executors={"PYTHONSTREAM": NFNPythonExecutorStreaming()},
                        ageing_interval=1)
nfn_fwd3.executors["PYTHONSTREAM"].initialize_executor(nfn_fwd3.nfnlayer.queue_to_lower, nfn_fwd3.nfnlayer.queue_from_lower, nfn_fwd3.nfnlayer.computation_table, nfn_fwd3.nfnlayer.cs, nfn_fwd3.icnlayer.pit, classic)

nfn_fwd4 = NFNForwarder(port=0, encoder=NdnTlvEncoder(),
                        interfaces=[simulation_bus.add_interface("nfn4")], log_level=255, executors={"PYTHONSTREAM": NFNPythonExecutorStreaming()},
                        ageing_interval=1)
nfn_fwd4.executors["PYTHONSTREAM"].initialize_executor(nfn_fwd4.nfnlayer.queue_to_lower, nfn_fwd4.nfnlayer.queue_from_lower, nfn_fwd4.nfnlayer.computation_table, nfn_fwd4.nfnlayer.cs, nfn_fwd4.icnlayer.pit, classic)

nfn_fwd5 = NFNForwarder(port=0, encoder=NdnTlvEncoder(),
                        interfaces=[simulation_bus.add_interface("nfn5")], log_level=255, executors={"PYTHONSTREAM": NFNPythonExecutorStreaming()},
                        ageing_interval=1)
nfn_fwd5.executors["PYTHONSTREAM"].initialize_executor(nfn_fwd5.nfnlayer.queue_to_lower, nfn_fwd5.nfnlayer.queue_from_lower, nfn_fwd5.nfnlayer.computation_table, nfn_fwd5.nfnlayer.cs, nfn_fwd5.icnlayer.pit, classic)


repo = ICNDataRepository("./InputFiles", Name("/repo/r1"), 0, 255, NdnTlvEncoder(), False, False, interfaces=[simulation_bus.add_interface("repo")])
repo.start_repo()

mgmt_client0 = MgmtClient(nfn_fwd0.mgmt.mgmt_sock.getsockname()[1])
mgmt_client1 = MgmtClient(nfn_fwd1.mgmt.mgmt_sock.getsockname()[1])
mgmt_client2 = MgmtClient(nfn_fwd2.mgmt.mgmt_sock.getsockname()[1])
mgmt_client3 = MgmtClient(nfn_fwd3.mgmt.mgmt_sock.getsockname()[1])
mgmt_client4 = MgmtClient(nfn_fwd4.mgmt.mgmt_sock.getsockname()[1])
mgmt_client5 = MgmtClient(nfn_fwd5.mgmt.mgmt_sock.getsockname()[1])

fetch_tool = Fetch("nfn0", None, 255, NdnTlvEncoder(), interfaces=[simulation_bus.add_interface("fetchtoo1")])

nfn_fwd0.start_forwarder()
nfn_fwd1.start_forwarder()
nfn_fwd2.start_forwarder()
nfn_fwd3.start_forwarder()
nfn_fwd4.start_forwarder()
nfn_fwd5.start_forwarder()

simulation_bus.start_process()

mgmt_client0.add_face("nfn1", None, 0)
mgmt_client0.add_forwarding_rule(Name("/lib"), [0])
mgmt_client1.add_face("nfn2", None, 0)
mgmt_client1.add_forwarding_rule(Name("/lib"), [0])
mgmt_client2.add_face("nfn3", None, 0)
mgmt_client2.add_forwarding_rule(Name("/lib"), [0])
mgmt_client3.add_face("nfn4", None, 0)
mgmt_client3.add_forwarding_rule(Name("/lib"), [0])
mgmt_client4.add_face("nfn5", None, 0)
mgmt_client4.add_forwarding_rule(Name("/lib"), [0])
mgmt_client5.add_face("repo", None, 0)
mgmt_client5.add_forwarding_rule(Name("/repo/r1"), [0])


mgmt_client0.add_new_content(Name("/lib/node0"),"PYTHONSTREAM\ngetnext_on_writeout\ndef getnext_on_writeout(arg):\n    print('Start sechste')\n    a = get_next(arg)\n    sleep(2)\n    b = get_next(arg)\n    sleep(2)\n    c = get_next(arg)\n    sleep(2)\n    d = get_next(arg)\n    sleep(2)\n    e = get_next(arg)\n    sleep(2)\n    f = get_next(arg)\n    sleep(2)\n    g = get_next(arg)\n    sleep(2)\n    h = get_next(arg)\n    sleep(2)\n    i = get_next(arg)\n    sleep(2)\n    j = get_next(arg)\n    sleep(2)\n    print('Ende sechste')\n    return a + b + c + d + e + f + g + h + i + j")

mgmt_client1.add_new_content(Name("/lib/node1"),"PYTHONSTREAM\nwriteout_on_getnext\ndef writeout_on_getnext(arg):\n    print('Start fünfte')\n    write_out_on_get_next(arg)\n    return print('Ende fünfte')\n")

mgmt_client2.add_new_content(Name("/lib/node2"),"PYTHONSTREAM\nwriteout_on_getnext\ndef writeout_on_getnext(arg):\n    print('Start vierte')\n    write_out_on_get_next(arg)\n    return print('Ende vierte')\n")

mgmt_client3.add_new_content(Name("/lib/node3"),"PYTHONSTREAM\nwriteout_on_getnext\ndef writeout_on_getnext(arg):\n    print('Start dritte')\n    write_out_on_get_next(arg)\n    return print('Ende dritte')\n")

mgmt_client4.add_new_content(Name("/lib/node4"),"PYTHONSTREAM\nwriteout_on_getnext\ndef writeout_on_getnext(arg):\n    print('Start zweite')\n    write_out_on_get_next(arg)\n    return print('Ende zweite')\n")

mgmt_client5.add_new_content(Name("/lib/node5"),"PYTHONSTREAM\nwriteout_on_getnext\ndef writeout_on_getnext(arg):\n    print('Start erste')\n    write_out_on_get_next(arg)\n    return print('Ende erste')\n")


scenario_node_5 = Name("/lib/node5")
scenario_node_5 += "#(=/repo/r1/exampleInputFile=)"
scenario_node_5 += "NFN"

scenario_node_4 = Name("/lib/node4")
scenario_node_4 += "#(=" + str(scenario_node_5) + "=)"
scenario_node_4 += "NFN"

scenario_node_3 = Name("/lib/node3")
scenario_node_3 += "#(=" + str(scenario_node_4) + "=)"
scenario_node_3 += "NFN"

scenario_node_2 = Name("/lib/node2")
scenario_node_2 += "#(=" + str(scenario_node_3) + "=)"
scenario_node_2 += "NFN"

scenario_node_1 = Name("/lib/node1")
scenario_node_1 += "#(=" + str(scenario_node_2) + "=)"
scenario_node_1 += "NFN"

scenario_node_0 = Name("/lib/node0")
scenario_node_0 += '_("' + str(scenario_node_1) + '")'
scenario_node_0 += "NFN"

time_list = []
for i in range (0, 10):
    start_time = time.perf_counter()
    res = fetch_tool.fetch_data(scenario_node_0, timeout=60)
    end_time = time.perf_counter()
    time_needed = end_time - start_time
    if res.startswith("Inhalt von name1. Inhalt von name2. Inhalt von name3. "):
        time_list.append(time_needed)
    else:
        print("Something went wrong")
        print("Something went wrong")
        print("Something went wrong")
        print("Something went wrong")

plt.plot([1, 2, 3, 4, 5, 6, 7, 8, 9 , 10], time_list, 'ro')
plt.axis([0, 11, -2, 23])
plt.xticks(np.arange(0, 11, 1))
plt.xlabel("run number")
plt.ylabel("time in s")
plt.title("Six hop scenario " + datetime.now().strftime("%H:%M:%S"))
plt.savefig('six_hop_scenario.png')
plt.show()

print("Time needed in seconds:", time_list)


nfn_fwd0.stop_forwarder()
nfn_fwd1.stop_forwarder()
nfn_fwd2.stop_forwarder()
nfn_fwd3.stop_forwarder()
nfn_fwd4.stop_forwarder()
nfn_fwd5.stop_forwarder()
repo.stop_repo()
fetch_tool.stop_fetch()
simulation_bus.stop_process()
mgmt_client0.shutdown()
mgmt_client1.shutdown()
mgmt_client2.shutdown()
mgmt_client3.shutdown()
mgmt_client4.shutdown()
mgmt_client5.shutdown()
