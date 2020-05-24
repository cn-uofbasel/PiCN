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
        for i in range(1, numberOfLines):
            f.write("/repo/r1/name" + str(i) + "\n")
            generateNameFiles(path, i)
        f.write("/repo/r1/name" + str(numberOfLines))
        generateNameFiles(path, numberOfLines)
    f.close()

generateExampleFiles("InputFiles/exampleInputFile", 10)

simulation_bus = SimulationBus(packetencoder=NdnTlvEncoder())

nfn_fwd0 = NFNForwarder(port=0, encoder=NdnTlvEncoder(),
                        interfaces=[simulation_bus.add_interface("nfn0")], log_level=255, executors={"PYTHONSTREAM": NFNPythonExecutorStreaming()},
                        ageing_interval=1)
nfn_fwd0.executors["PYTHONSTREAM"].initialize_executor(nfn_fwd0.nfnlayer.queue_to_lower, nfn_fwd0.nfnlayer.queue_from_lower, nfn_fwd0.nfnlayer.computation_table, nfn_fwd0.nfnlayer.cs, nfn_fwd0.icnlayer.pit)

nfn_fwd1 = NFNForwarder(port=0, encoder=NdnTlvEncoder(),
                        interfaces=[simulation_bus.add_interface("nfn1")], log_level=255, executors={"PYTHONSTREAM": NFNPythonExecutorStreaming()},
                        ageing_interval=1)
nfn_fwd1.executors["PYTHONSTREAM"].initialize_executor(nfn_fwd1.nfnlayer.queue_to_lower, nfn_fwd1.nfnlayer.queue_from_lower, nfn_fwd1.nfnlayer.computation_table, nfn_fwd1.nfnlayer.cs, nfn_fwd1.icnlayer.pit)


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
mgmt_client1.add_face("repo", None, 0)
mgmt_client1.add_forwarding_rule(Name("/repo/r1"), [0])

mgmt_client1.add_new_content(Name("/lib/checkStreamFunc"),"PYTHONSTREAM\ncheckStreamFunc\ndef checkStreamFunc(content):\n    res = checkStreaming(content)\n    return res")
mgmt_client1.add_new_content(Name("/lib/getNext"),"PYTHONSTREAM\ngetNext\ndef getNext(arg):\n    a = get_next(arg)\n    b = get_next(arg)\n    c = get_next(arg)\n    d = get_next(arg)\n    return a + b + c + d")
mgmt_client1.add_new_content(Name("/lib/writeOutTest"),"PYTHONSTREAM\nwriteOutTest\ndef writeOutTest(arg):\n    a = get_next(arg)\n    return a, write_out(a)")

mgmt_client1.add_new_content(Name("/repo/r1/writeOutInputFile/streaming/p0"), "Hello ")
mgmt_client1.add_new_content(Name("/repo/r1/writeOutInputFile/streaming/p1"), "world! ")
mgmt_client1.add_new_content(Name("/repo/r1/writeOutInputFile/streaming/p2"), "This is ")
mgmt_client1.add_new_content(Name("/repo/r1/writeOutInputFile/streaming/p3"), "just a test.")
mgmt_client1.add_new_content(Name("/repo/r1/writeOutInputFile/streaming/p4"), "sdo:endstreaming")


checkStreamFuncTest = Name("/lib/checkStreamFunc")
checkStreamFuncTest += '_(/repo/r1/exampleInputFile)'
checkStreamFuncTest += "NFN"

getNextTest = Name("/lib/getNext")
getNextTest += '_(/repo/r1/exampleInputFile)'
getNextTest += "NFN"

writeOutTest = Name("/lib/writeOutTest")
writeOutTest += '_(/repo/r1/exampleInputFile)'
writeOutTest += "NFN"

res = fetch_tool.fetch_data(writeOutTest)
print("Interest result: ", res)


nfn_fwd0.stop_forwarder()
nfn_fwd1.stop_forwarder()
repo.stop_repo()
fetch_tool.stop_fetch()
simulation_bus.stop_process()
mgmt_client0.shutdown()
mgmt_client1.shutdown()
