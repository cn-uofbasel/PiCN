"""A model for simulating a stationary node in the simulation"""

from PiCN.Simulations.MobilitySimulations.Model.SimulationNode import SimulationNode
from PiCN.ProgramLibs.NFNForwarder.NFNForwarder import NFNForwarder
from PiCN.Mgmt import MgmtClient


class StationaryNode(SimulationNode):
    """A model representing a stationary node, e.g., an edge node such as a road side unit, etc."""

    ############################
    # INIT
    ############################

    def __init__(self, node_id: int, com_range: float, forwarder: NFNForwarder = None, mgmt_tool: MgmtClient = None):
        """
        param: node_id: the identifier of the node within the simulation
        param: com_range: the communication rang of the stationary node in km; values range from 0-2
        param: forwarder: the NFN forwarder to be installed on the stationary node
        param: mgmt_tool: the mgmt tool client to be installed on the stationary node
        """
        super().__init__(node_id=node_id)
        self._com_range = com_range
        assert (0 <= self._com_range <= 2), \
            "Communication range of the stationary node ranging from 0-2 km"
        self._forwarder = forwarder
        self._mgmt_tool = mgmt_tool

    ############################
    # METHODS
    ############################

    @property
    def com_range(self) -> float:
        """
        Getter for the communication range in km
        """
        return self._com_range

    @property
    def nfn_forwarder(self) -> NFNForwarder:
        """
        Getter for the configured NFN forwarder of the stationary node
        """
        return self._forwarder

    @nfn_forwarder.setter
    def nfn_forwarder(self, forwarder: NFNForwarder):
        """
        Setter of the forwarder to be installed at the stationary node
        :param forwarder: the forwarder to be set
        """
        self._forwarder = forwarder

    @property
    def mgmt_tool(self) -> MgmtClient:
        """
        Getter for the configured MgmtClient of the stationary node
        """
        return self._mgmt_tool

    @mgmt_tool.setter
    def mgmt_tool(self, mgmt_tool: MgmtClient):
        """
        Setter of the management client to be installed at the stationary node
        :param mgmt_tool: the management client to be installed
        """
        self._mgmt_tool = mgmt_tool
