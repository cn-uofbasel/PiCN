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

    def test_compute_fwd(self):
        """Test if computation forward is correct"""
        name1 = Name("/test/data/d3")
        name1 += "/func/f1(_)"
        name1 += "NFN"
        name2 = Name("/func/f1")
        name2 += "_(/test/data/d3)"
        name2 += "NFN"
        self.planTable.add_plan(name1, [name2], 5)
        res1 = self.planTable.compute_fwd(name1)
        self.assertTrue(res1)
        name3 = Name("/func/f1")
        name3 += "_(/test/data/d4)"
        name3 += "NFN"
        res2 = self.planTable.compute_fwd(name3)
        self.assertFalse(res2)

    def test_compute_fwd_subcomps(self):
        """Test if computation forward is correct for subcomps"""
        name1 = Name("/test/data/d1")
        name2 = Name("/hello/world/d2")
        name3 = Name("/test/data/d3")
        name3 += "/func/f1(_)"
        name3 += "NFN"
        self.planTable.add_plan(name1, [name2, name3], 5)

        res1 = self.planTable.compute_fwd(name1)
        self.assertFalse(res1)
        res2 = self.planTable.compute_fwd(name2)
        self.assertTrue(res2)
        res3 = self.planTable.compute_fwd(name3)
        self.assertTrue(res3)

        name4 = Name("/func/f1")
        name4 += "_(/test/data/d3)"
        name4 += "NFN"

        res4 = self.planTable.compute_fwd(name4)
        self.assertTrue(res4)

        name5 = Name("/func/f1")
        name5 += "_(/test/data/d4)"
        name5 += "NFN"

        res5 = self.planTable.compute_fwd(name5)
        self.assertFalse(res5)

    def test_rewrite(self):
        """Test rewrites"""
        pass

    def test_rewrite_subcomp(self):
        """Test rewrites for subcomp"""
        pass