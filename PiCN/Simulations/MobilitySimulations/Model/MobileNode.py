"""A model for simulating a mobile node which moves with certain speed and direction through the simulation"""

from PiCN.Simulations.MobilitySimulations.Model.SimulationNode import SimulationNode


class MobileNode(SimulationNode):
    """A model representing a mobile node, e.g., a vehicle, pedestrian, etc."""

    def __init__(self, node_id: str, speed: int, direction: int):
        """
        param: node_id: the identifier of the node within the simulation
        param: speed: the traveling speed of the mobile node in km/h; values range from 0-250
        param: direction: the heading direction of the mobile node within the simulation; Since the simulation allows
        for 1-dimensional simulations, the direction values are: -1 and 1
        """
        super().__init__(node_id=node_id)
        self._speed = speed
        # check if the speed value is appropriately selected
        assert (0 <= self._speed <= 250), \
            "Only values ranging from 0-250 km/h are allowed for the mobile node speed"
        self._direction = direction
        # check if the direction value is appropriately selected
        assert (-1 == self._direction or self._direction == 1), \
            "Only -1 or 1 are allowed for heading directions of a mobile node"

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
