"""A test class for the mobile node simulation model"""

import unittest

from PiCN.Simulations.MobilitySimulations.Model.MobileNode import MobileNode


class TestMobileNode(unittest.TestCase):
    """test class to test the behavior of the mobile node simulation model"""

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

    def test_init_mobile_node(self):
        """tests if a mobile node is initialized correctly"""
        self.assertIsNotNone(MobileNode(node_id=1, spawn_point=0, speed=50, direction=-1))

    def test_init_mobile_node_wrong_parameter_speed(self):
        """tests if the speed is in the expected range 0-250 """
        # lower boundary error
        with self.assertRaises(AssertionError):
            MobileNode(node_id=1, spawn_point=0, speed=-1, direction=-1)
        # upper boundary error
        with self.assertRaises(AssertionError):
            MobileNode(node_id=1, spawn_point=0, speed=251, direction=-1)

    def test_init_mobile_node_wrong_parameter_value_direction(self):
        """tests if the direction value is expected range"""
        # lower boundary error
        with self.assertRaises(AssertionError):
            MobileNode(node_id=1, spawn_point=0, speed=50, direction=-2)
        # in between error
        with self.assertRaises(AssertionError):
            MobileNode(node_id=1, spawn_point=0, speed=50, direction=0)
        # upper boundary error
        with self.assertRaises(AssertionError):
            MobileNode(node_id=1, spawn_point=0, speed=50, direction=2)
