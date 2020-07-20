import time
from PiCN.Layers.NFNLayer.NFNExecutor.NFNPythonExecutorStreaming import NFNPythonExecutorStreaming
from PiCN.ProgramLibs.Fetch import Fetch
from PiCN.ProgramLibs.ICNDataRepository import ICNDataRepository
from PiCN.ProgramLibs.NFNForwarder import NFNForwarder
from PiCN.Layers.LinkLayer.Interfaces import SimulationBus
from PiCN.Layers.PacketEncodingLayer.Encoder import NdnTlvEncoder
from PiCN.Mgmt import MgmtClient
from PiCN.Packets import Name

def pathDetection(fileName: str):
    pathList = fileName.split("/")
    path = ""
    for j in range(0, len(pathList) - 1):
        if j is 0:
            path = path + pathList[j]
        else:
            path = path + "/" + pathList[j]
    return path + "/"

def generateNameFiles(path: str, number: int):
    with open(path + "name" + str(number), "w") as f:
        f.write("Content of name" + str(number) + ". ")
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


def ageing():
    return


def simulation(classic, amount_of_parts):
    generateExampleFiles("../InputFiles/exampleInputFile", amount_of_parts)

    simulation_bus = SimulationBus(packetencoder=NdnTlvEncoder())

    nfn_fwd0 = NFNForwarder(port=0, encoder=NdnTlvEncoder(),
                            interfaces=[simulation_bus.add_interface("nfn0")], log_level=255, executors={"PYTHONSTREAM": NFNPythonExecutorStreaming()},
                            ageing_interval=1)
    nfn_fwd0.executors["PYTHONSTREAM"].initialize_executor(nfn_fwd0.nfnlayer.queue_to_lower, nfn_fwd0.nfnlayer.queue_from_lower, nfn_fwd0.nfnlayer.cs, classic)
    nfn_fwd0.icnlayer.pit.ageing = ageing
    nfn_fwd0.timeoutpreventionlayer.ageing = ageing

    nfn_fwd1 = NFNForwarder(port=0, encoder=NdnTlvEncoder(),
                            interfaces=[simulation_bus.add_interface("nfn1")], log_level=255, executors={"PYTHONSTREAM": NFNPythonExecutorStreaming()},
                            ageing_interval=1)
    nfn_fwd1.executors["PYTHONSTREAM"].initialize_executor(nfn_fwd1.nfnlayer.queue_to_lower, nfn_fwd1.nfnlayer.queue_from_lower, nfn_fwd1.nfnlayer.cs, classic)
    nfn_fwd1.icnlayer.pit.ageing = ageing
    nfn_fwd1.timeoutpreventionlayer.ageing = ageing

    nfn_fwd2 = NFNForwarder(port=0, encoder=NdnTlvEncoder(),
                            interfaces=[simulation_bus.add_interface("nfn2")], log_level=255, executors={"PYTHONSTREAM": NFNPythonExecutorStreaming()},
                            ageing_interval=1)
    nfn_fwd2.executors["PYTHONSTREAM"].initialize_executor(nfn_fwd2.nfnlayer.queue_to_lower, nfn_fwd2.nfnlayer.queue_from_lower, nfn_fwd2.nfnlayer.cs, classic)
    nfn_fwd2.icnlayer.pit.ageing = ageing
    nfn_fwd2.timeoutpreventionlayer.ageing = ageing


    repo = ICNDataRepository("../InputFiles", Name("/repo/r1"), 0, 255, NdnTlvEncoder(), False, False, interfaces=[simulation_bus.add_interface("repo")])
    repo.start_repo()

    mgmt_client0 = MgmtClient(nfn_fwd0.mgmt.mgmt_sock.getsockname()[1])
    mgmt_client1 = MgmtClient(nfn_fwd1.mgmt.mgmt_sock.getsockname()[1])
    mgmt_client2 = MgmtClient(nfn_fwd2.mgmt.mgmt_sock.getsockname()[1])

    fetch_tool = Fetch("nfn0", None, 255, NdnTlvEncoder(), interfaces=[simulation_bus.add_interface("fetchtoo1")])

    nfn_fwd0.start_forwarder()
    nfn_fwd1.start_forwarder()
    nfn_fwd2.start_forwarder()

    simulation_bus.start_process()

    mgmt_client0.add_face("nfn1", None, 0)
    mgmt_client0.add_forwarding_rule(Name("/lib"), [0])
    mgmt_client1.add_face("nfn2", None, 0)
    mgmt_client1.add_forwarding_rule(Name("/lib"), [0])
    mgmt_client2.add_face("repo", None, 0)
    mgmt_client2.add_forwarding_rule(Name("/repo/r1"), [0])


    mgmt_client0.add_new_content(Name("/lib/node0"),"PYTHONSTREAM\ngetnext_on_writeout\ndef getnext_on_writeout(arg):\n    print('Start dritte')\n    res = ''\n    a = get_next(arg)\n    while a != None:\n        a = a.lower()\n        sleep(1)\n        res = res + a\n        a = get_next(arg)\n    print('Ende dritte')\n    return res")

    mgmt_client1.add_new_content(Name("/lib/node1"),"PYTHONSTREAM\nwriteout_on_getnext\ndef writeout_on_getnext(arg):\n    print('Start zweite')\n    write_out_on_get_next(arg)\n    return print('Ende zweite')\n")

    mgmt_client2.add_new_content(Name("/lib/node2"),"PYTHONSTREAM\nwriteout_on_getnext\ndef writeout_on_getnext(arg):\n    print('Start erste')\n    a = get_next(arg)\n    while a and check_end_streaming(a) is False:\n        a = a.upper()\n        sleep(1)\n        write_out(a)\n        a = get_next(arg)\n    last_write_out()\n    return print('Ende erste')\n")

    scenario_node_2 = Name("/lib/node2")
    scenario_node_2 += "#(=/repo/r1/exampleInputFile=)"
    scenario_node_2 += "NFN"

    scenario_node_1 = Name("/lib/node1")
    scenario_node_1 += "#(=" + str(scenario_node_2) + "=)"
    scenario_node_1 += "NFN"
    scenario_node_0 = Name("/lib/node0")
    scenario_node_0 += '_("' + str(scenario_node_1) + '")'
    scenario_node_0 += "NFN"


    start_time = time.perf_counter()
    res = fetch_tool.fetch_data(scenario_node_0, timeout=60)
    end_time = time.perf_counter()
    time_needed = end_time - start_time


    if res.startswith("content of name"):
        print("Time:", time_needed, res)
        return time_needed
    else:
        print("Something went wrong")
        None