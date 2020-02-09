"""A model for simulating a stationary node in the simulation"""

from PiCN.Simulations.MobilitySimulations.Model.SimulationNode import SimulationNode


class StationaryNode(SimulationNode):
    """A model representing a stationary node, e.g., an edge node such as a road side unit, etc."""

    ############################
    # INIT
    ############################

    def __init__(self, node_id: str, com_range: float):
        """
        param: node_id: the identifier of the node within the simulation
        param: com_range: the communication rang of the stationary node in km; values range from 0-2
        """
        super().__init__(node_id=node_id)
        self._com_range = com_range
        assert (0 <= self._com_range <= 2), \
            "Communication range of the stationary node ranging from 0-2 km"

    ############################
    # METHODS
    ############################

    @property
    def com_range(self) -> float:
        """
        Getter for the communication range in km
        """
        return self._com_range
