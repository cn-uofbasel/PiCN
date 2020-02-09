"""A model for simulating any node in the simulation"""


class SimulationNode(object):
    """A model used within the simulation to simulate the behavior of a certain node"""

    ################################
    # CONSTRUCTOR
    ################################

    def __init__(self, node_id: str):
        """
        Constructor of the node
        """
        self._node_id = node_id

    ################################
    # METHODS
    ################################

    @property
    def node_id(self) -> str:
        """
        Getter of the node id as string
        """
        return self._node_id
