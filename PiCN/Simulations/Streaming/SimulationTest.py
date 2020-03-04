from PiCN.ProgramLibs.Fetch import Fetch
from PiCN.ProgramLibs.ICNDataRepository import ICNDataRepository
from PiCN.ProgramLibs.NFNForwarder import NFNForwarder
from PiCN.Layers.LinkLayer.Interfaces import SimulationBus
from PiCN.Layers.PacketEncodingLayer.Encoder import NdnTlvEncoder
from PiCN.Mgmt import MgmtClient
from PiCN.Packets import Name


simulation_bus = SimulationBus(packetencoder=NdnTlvEncoder())
nfn_fwd0 = NFNForwarder(port=0, encoder=NdnTlvEncoder(),
                        interfaces=[simulation_bus.add_interface("nfn0")], log_level=255,
                        ageing_interval=1)


nfn_fwd1 = NFNForwarder(port=0, encoder=NdnTlvEncoder(),
                        interfaces=[simulation_bus.add_interface("nfn1")], log_level=255,
                        ageing_interval=1)

repo = ICNDataRepository("./InputFiles", Name("/repo/r1"), 0, 255, NdnTlvEncoder(), False, False, interfaces=[simulation_bus.add_interface("repo")])
repo.start_repo()
# print('Output von repo.repolayer._repository.get_content(Name("/repo/r1/exampleInputFile")).content:\n', repo.repolayer._repository.get_content(Name("/repo/r1/exampleInputFile")).content)

mgmt_client0 = MgmtClient(nfn_fwd0.mgmt.mgmt_sock.getsockname()[1])
mgmt_client1 = MgmtClient(nfn_fwd1.mgmt.mgmt_sock.getsockname()[1])

fetch_tool = Fetch("nfn0", None, 255, NdnTlvEncoder(), interfaces=[simulation_bus.add_interface("fetchtool1")])

nfn_fwd0.start_forwarder()
nfn_fwd1.start_forwarder()
simulation_bus.start_process()

mgmt_client0.add_face("nfn1", None, 0)
mgmt_client0.add_forwarding_rule(Name("/repo/r1"), [0])
mgmt_client1.add_face("repo", None, 0)
mgmt_client1.add_forwarding_rule(Name("/repo/r1"), [0])

res = fetch_tool.fetch_data(Name("/repo/r1/exampleInputFile"))
print(res)

nfn_fwd0.stop_forwarder()
nfn_fwd1.stop_forwarder()
repo.stop_repo()
fetch_tool.stop_fetch()
simulation_bus.stop_process()
mgmt_client0.shutdown()
mgmt_client1.shutdown()
