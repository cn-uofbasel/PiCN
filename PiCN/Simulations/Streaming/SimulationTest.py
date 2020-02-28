from PiCN.ProgramLibs.Fetch import Fetch
from PiCN.ProgramLibs.ICNDataRepository import ICNDataRepository
from PiCN.ProgramLibs.NFNForwarder import NFNForwarder
from PiCN.Layers.LinkLayer.Interfaces import SimulationBus
from PiCN.Layers.LinkLayer.Interfaces import AddressInfo
from PiCN.Layers.PacketEncodingLayer.Encoder import BasicEncoder, SimpleStringEncoder, NdnTlvEncoder
from PiCN.Mgmt import MgmtClient
from PiCN.Packets import Content, Interest, Name


simulation_bus = SimulationBus(packetencoder=NdnTlvEncoder())
nfn_fwd0 = NFNForwarder(port=0, encoder=NdnTlvEncoder(),
                        interfaces=[simulation_bus.add_interface("nfn0")], log_level=255,
                        ageing_interval=1)

nfn_fwd1 = NFNForwarder(port=0, encoder=NdnTlvEncoder(),
                        interfaces=[simulation_bus.add_interface("nfn1")], log_level=255,
                        ageing_interval=1)

# TODO: Create the repository
repo1 = ICNDataRepository("/InputFiles/exampleInputFile.txt", Name("/repo/r1"), 0, 255, NdnTlvEncoder(), False, False,
                                       [simulation_bus.add_interface("repo1")])

mgmt_client0 = MgmtClient(nfn_fwd0.mgmt.mgmt_sock.getsockname()[1])
mgmt_client1 = MgmtClient(nfn_fwd1.mgmt.mgmt_sock.getsockname()[1])

fetch_tool = Fetch("nfn0", None, 255, NdnTlvEncoder(), interfaces=[simulation_bus.add_interface("fetchtool1")])

nfn_fwd0.start_forwarder()
nfn_fwd1.start_forwarder()
simulation_bus.start_process()

mgmt_client0.add_face("nfn1", None, 0)
# TODO: Create face from nfn_fwd1 to repo1
mgmt_client1.add_face("repo1", None, 0)


mgmt_client0.add_forwarding_rule(Name("/data"), [0])
# TODO: Create forwarding rule from nfn_fwd1 to the repo1
mgmt_client1.add_forwarding_rule(Name("/repo/r1"), [0])


# Can't be used for this example...
#
# mgmt_client0.add_new_content(Name("/func/combine"), "PYTHON\nfunc\ndef func(a, b):\n    return a + b")
# mgmt_client1.add_new_content(Name("/data/obj1"), "World")
#
# name = Name("/func/combine")
# name += '_("Hello",/data/obj1)'
# name += "NFN"
#
# res = fetch_tool.fetch_data(name, timeout=20)
# print(res)

nfn_fwd0.stop_forwarder()
nfn_fwd1.stop_forwarder()
# TODO: Stop repo1
repo1.stop_repo()
fetch_tool.stop_fetch()
simulation_bus.stop_process()
mgmt_client0.shutdown()
mgmt_client1.shutdown()
