"""Simulation environment to test long-term sessions.
This is part of the bachelors thesis by Luc Kury@2020."""

from PiCN.ProgramLibs.Fetch import Fetch
from PiCN.ProgramLibs.ICNDataRepository import ICNDataRepository
from PiCN.ProgramLibs.ICNForwarder import ICNForwarder
from PiCN.Layers.LinkLayer.Interfaces import SimulationBus
from PiCN.Mgmt import MgmtClient
from PiCN.Packets import Content, Interest, Name

import types


def setup(dummy):
    dummy.simulation_bus = SimulationBus()  # Use BasicStringEncoder
    dummy.icn_repo0 = ICNDataRepository(port=0, prefix=Name("/test/t1"), foldername=None, interfaces=[dummy.simulation_bus.add_interface("repo0")], log_level=255)  # Initialize repository 0
    dummy.icn_repo1 = ICNDataRepository(port=0, prefix=Name("/test/t2"), foldername=None, interfaces=[dummy.simulation_bus.add_interface("repo1")], log_level=255)  # Initialize repository 1 (this one has sessions)

    dummy.icn_forwarder0 = ICNForwarder(port=0, log_level=255, interfaces=[dummy.simulation_bus.add_interface("fw0")])  # Initialize forwarder 0
    dummy.icn_forwarder1 = ICNForwarder(port=0, interfaces=[dummy.simulation_bus.add_interface("fw1")])  # Initialize forwarder 1

    dummy.mgmt_client0 = MgmtClient(dummy.icn_repo0.mgmt.mgmt_sock.getsockname()[1])  # Mgmt client for repository 0
    dummy.mgmt_client1 = MgmtClient(dummy.icn_repo1.mgmt.mgmt_sock.getsockname()[1])  # Mgmt client for repository 1
    dummy.mgmt_client2 = MgmtClient(dummy.icn_forwarder0.mgmt.mgmt_sock.getsockname()[1])  # Mgmt client for forwarder 0
    dummy.mgmt_client3 = MgmtClient(dummy.icn_forwarder1.mgmt.mgmt_sock.getsockname()[1])  # Mgmt client for forwarder 1

    # This is unintuitive. Why does the fetch tool add its own face, but the other components don't?
    dummy.fetch_tool = Fetch("fw0", None, log_level=255, interfaces=[dummy.simulation_bus.add_interface("fetcht0")])  # Initialize a client (fetch tool)

    dummy.icn_repo0.start_repo()
    dummy.icn_repo1.start_repo()
    dummy.icn_forwarder0.start_forwarder()
    dummy.icn_forwarder1.start_forwarder()
    dummy.simulation_bus.start_process()

    dummy.mgmt_client2.add_face("repo0", None, 0)  # Add a connection between fw0 and repo0 interface
    dummy.mgmt_client2.add_forwarding_rule(Name("/test/t1"), [0])  # Add a rule to forward packages with this prefix to this forwarder.
    # dummy.mgmt_client0.add_forwarding_rule(Name("/test/t1"), [0])  # Add
    dummy.mgmt_client3.add_face("repo1", None, 0)  # Add a network interface to forwarder 0 and give it ip and port
    dummy.mgmt_client3.add_forwarding_rule(Name("/test/t2"), [0])  # Add

    # dummy.mgmt_client0.add_face("repo0", None, 0)  # Add a network interface to forwarder 0 and give it ip and port
    # dummy.mgmt_client0.add_forwarding_rule(Name("/test/t1"), [0])  # Add
    # dummy.mgmt_client1.add_face("repo1", None, 0)  # Add a network interface to forwarder 0 and give it ip and port
    # dummy.mgmt_client1.add_forwarding_rule(Name("/test/t2"), [0])  # Add

    dummy.icn_repo0.repolayer._repository.add_content(Name("/test/t1/content_object"), "This is just a test for repo0.")
    dummy.mgmt_client1.add_new_content(Name("/test/t2/session_connector"), "This shouldn't be needed.")

    interest0 = Name("/test/t1/content_object")
    interest1 = Name("/test/t2/session_connector")

    res0 = dummy.fetch_tool.fetch_data(interest0, timeout=20)
    #res1 = dummy.fetch_tool.fetch_data(interest1, timeout=20)

    print(res0)
    #print(res1)


def teardown(dummy):
    dummy.icn_forwarder0.stop_forwarder()
    dummy.icn_forwarder1.stop_forwarder()
    dummy.fetch_tool.stop_fetch()
    dummy.simulation_bus.stop_process()
    dummy.mgmt_client0.shutdown()
    dummy.mgmt_client1.shutdown()
    dummy.mgmt_client2.shutdown()
    dummy.mgmt_client3.shutdown()


if __name__ == "__main__":
    dummy = types.SimpleNamespace()
    setup(dummy)
    teardown(dummy)
