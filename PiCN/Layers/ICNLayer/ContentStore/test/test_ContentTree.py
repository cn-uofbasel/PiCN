"""Tests for the ContentTree data structure"""

import unittest

from PiCN.Layers.ICNLayer.ContentStore.ContentTree import ContentTree
from PiCN.Packets import Content


class test_ContentTree(unittest.TestCase):

    def setUp(self):
        self.tree = ContentTree()

    def tearDown(self):
        pass

    def test_insert(self):
        c1 = Content("/ndn/ch/unibas/foo1", "unibas-foo1")
        c2 = Content("/ndn/ch/unibas/foo2", "unibas-foo2")
        c3 = Content("/ndn/ch/unibas/foo/bar1", "unibas-foo-bar1")
        c4 = Content("/ndn/ch/unibas/foo3", "unibas-foo3")
        c5 = Content("/ndn/ch/unibas/foo/bar2", "unibas-foo-bar2")
        c6 = Content("/ndn/ch/unibas/foo4", "unibas-foo4")
        c7 = Content("/ndn/ch", "ndn-ch")
        self.tree.insert(c1.name.components, c1)
        self.tree.insert(c2.name.components, c2)
        self.tree.insert(c3.name.components, c3)
        self.tree.insert(c4.name.components, c4)
        self.tree.insert(c5.name.components, c5)
        self.tree.insert(c6.name.components, c6)
        self.tree.insert(c7.name.components, c7)