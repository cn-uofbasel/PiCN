"""A test class for the stationary node simulation model"""

import unittest

from PiCN.Simulations.MobilitySimulations.Model.StationaryNode import StationaryNode


class TestStationaryNode(unittest.TestCase):
    """test class to test the behavior of the stationary node simulation model"""

    ############################
    # TEST CONFIG
    ############################

    def setUp(self) -> None:
        pass

    def tearDown(self) -> None:
        pass

    ############################
    # TESTS
    ############################

    def test_init_stationary_node(self):
        """tests if a stationary node is initialized correctly"""
        self.assertIsNotNone(StationaryNode(node_id=1, com_range=0.5))

    def test_init_stationary_node_wrong_parameter_com_range(self):
        """tests if the communication range is in the expected range 0-2 km """
        # lower boundary error
        with self.assertRaises(AssertionError):
            StationaryNode(node_id=1, com_range=-1)
        # upper boundary error
        with self.assertRaises(AssertionError):
            StationaryNode(node_id=1, com_range=2.1)

