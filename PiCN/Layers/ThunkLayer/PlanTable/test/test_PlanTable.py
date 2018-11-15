"""Testing the plan table"""

import unittest

from PiCN.Layers.ThunkLayer.PlanTable import PlanTable
from PiCN.Packets import Name
from PiCN.Layers.NFNLayer.Parser import DefaultNFNParser

class test_PlanTable(unittest.TestCase):
    """Testing the plan table"""

    def setUp(self):
        self.planTable = PlanTable(DefaultNFNParser())

    def test_add_entry(self):
        name = Name("/test/data")
        requests = [Name("/test/data/d1"), Name("/test/data/d2"), Name("/test/data/d3")]
        cost = 3
        self.planTable.add_plan(name, requests, cost)
        self.assertEqual(self.planTable.container.get(name), (requests, cost))

    def test_get_plan(self):
        name = Name("/test/data")
        requests = [Name("/test/data/d1"), Name("/test/data/d2"), Name("/test/data/d3")]
        cost = 3
        self.planTable.add_plan(name, requests, cost)
        res = self.planTable.get_plan(name)
        self.assertEqual(requests, res)

    def test_get_cost(self):
        name = Name("/test/data")
        requests = [Name("/test/data/d1"), Name("/test/data/d2"), Name("/test/data/d3")]
        cost = 3
        self.planTable.add_plan(name, requests, cost)
        res = self.planTable.get_cost(name)
        self.assertEqual(cost, res)

    def test_get_plan_not_available(self):
        name = Name("/test/data")
        requests = [Name("/test/data/d1"), Name("/test/data/d2"), Name("/test/data/d3")]
        cost = 3
        self.planTable.add_plan(name, requests, cost)
        res = self.planTable.get_plan(Name("/test/data2"))
        self.assertIsNone(res)

    def test_get_cost_not_available(self):
        name = Name("/test/data")
        requests = [Name("/test/data/d1"), Name("/test/data/d2"), Name("/test/data/d3")]
        cost = 3
        self.planTable.add_plan(name, requests, cost)
        res = self.planTable.get_cost(Name("/test/data2"))
        self.assertIsNone(res)
