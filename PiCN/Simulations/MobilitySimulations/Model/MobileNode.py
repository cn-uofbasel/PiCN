"""A model for simulating a mobile node which moves with certain speed and direction through the simulation"""

from PiCN.Simulations.MobilitySimulations.Model.SimulationNode import SimulationNode
from PiCN.ProgramLibs.Fetch import Fetch
from PiCN.ProgramLibs.ICNForwarder import ICNForwarder
from PiCN.Mgmt import MgmtClient


class MobileNode(SimulationNode):
    """A model representing a mobile node, e.g., a vehicle, pedestrian, etc."""

    def __init__(self, node_id: int, spawn_point: int, speed: int, direction: int, forwarder: ICNForwarder = None,
                 fetch_tool: Fetch = None, mgmt_tool: MgmtClient = None):
        """
        :param node_id: the identifier of the node within the simulation
        :param spawn_point: the position of the node to start the simulation
        :param speed: the traveling speed of the mobile node in km/h; values range from 0-250
        :param direction: the heading direction of the mobile node within the simulation; Since the simulation allows
        for 1-dimensional simulations, the direction values are: -1 and 1
        :param forwarder: the forwarder at the mobile node to be installed
        :param fetch_tool: the fetch tool to be installed at the mobile node
        :param mgmt_tool: the mgmt tool to be installed at the mobile node
        """
        super().__init__(node_id=node_id,)
        self._spawn_point = spawn_point
        self._speed = speed
        # check if the speed value is appropriately selected
        assert (0 <= self._speed <= 250), \
            "Only values ranging from 0-250 km/h are allowed for the mobile node speed"
        self._direction = direction
        # check if the direction value is appropriately selected
        assert (-1 == self._direction or self._direction == 1), \
            "Only -1 or 1 are allowed for heading directions of a mobile node"
        self._forwarder = forwarder
        self._fetch = fetch_tool
        self._mgmt_tool = mgmt_tool

    @property
    def spawn_point(self):
        """
        Getter of the position the node starts the simulation
        """
        return self._spawn_point

    @property
    def speed(self) -> int:
        """
        Getter of the speed of the mobile node in km/h
        """
        return self._speed

    @property
    def direction(self) -> int:
        """
        Getter of the heading direction of the mobile node
        """
        return self._direction

    @property
    def forwarder(self) -> ICNForwarder:
        """
        Getter of the forwarder installed
        """
        return self._forwarder

    @forwarder.setter
    def forwarder(self, forwarder: ICNForwarder):
        """
        Setter of the forwarder to be installed
        :param the forwarder to be installed
        """
        self._forwarder = forwarder

    @property
    def fetch(self) -> Fetch:
        """
        Getter of the fetch tool installed at the node
        """
        return self._fetch

    @fetch.setter
    def fetch(self, fetch: Fetch):
        """
        Setter of the fetch tool to be installed
        """
        self._fetch = fetch

    @property
    def mgmt_tool(self) -> MgmtClient:
        """
        Getter of the mgmt client tool installed at the node
        """
        return self._mgmt_tool

    @mgmt_tool.setter
    def mgmt_tool(self, mgmt_tool: MgmtClient):
        """
        Setter of the mgmt client tool to be installed at the node
        """
        self._mgmt_tool = mgmt_tool
