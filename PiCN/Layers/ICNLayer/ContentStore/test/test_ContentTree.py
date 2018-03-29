"""Tests for the ContentTree data structure"""

import unittest

from PiCN.Layers.ICNLayer.ContentStore.ContentTree import ContentTree
from PiCN.Packets import Content, Name


class test_ContentTree(unittest.TestCase):

    def setUp(self):
        self.tree = ContentTree()

    def tearDown(self):
        pass

    def test_empty_tree(self):
        n = Name("/does/not/exist")
        self.tree.exact_lookup(n)
        self.tree.remove(n)

    def test_insert_and_exact_lookup(self):
        # create content objects
        c1 = Content("/ndn/ch/unibas/foo1", "unibas-foo1")
        c2 = Content("/ndn/ch/unibas/foo2", "unibas-foo2")
        c3 = Content("/ndn/ch/unibas/foo/bar1", "unibas-foo-bar1")
        c4 = Content("/ndn/ch/unibas/foo3", "unibas-foo3")
        c5 = Content("/ndn/ch/unibas/foo/bar2", "unibas-foo-bar2")
        c6 = Content("/ndn/ch/unibas/foo4", "unibas-foo4")
        c7 = Content("/ndn/ch", "ndn-ch")
        # insert
        self.tree.insert(c1)
        self.tree.insert(c2)
        self.tree.insert(c3)
        self.tree.insert(c4)
        self.tree.insert(c5)
        self.tree.insert(c6)
        self.tree.insert(c7)
        # exact lookup
        self.assertEqual(self.tree.exact_lookup(c1.name), c1)
        self.assertEqual(self.tree.exact_lookup(c2.name), c2)
        self.assertEqual(self.tree.exact_lookup(c3.name), c3)
        self.assertEqual(self.tree.exact_lookup(c4.name), c4)
        self.assertEqual(self.tree.exact_lookup(c5.name), c5)
        self.assertEqual(self.tree.exact_lookup(c6.name), c6)
        self.assertEqual(self.tree.exact_lookup(c7.name), c7)
        self.assertEqual(self.tree.exact_lookup(Name("/ndn")), None)
        self.assertEqual(self.tree.exact_lookup(Name("/unknown")), None)
        self.assertEqual(self.tree.exact_lookup(Name("/ndn/ch/unknown")), None)
        self.assertEqual(self.tree.exact_lookup(Name("/ndn/ch/unibas/foo1/unknown")), None)

    def test_insert_remove_exact_lookup(self):
        # create content objects
        c1 = Content("/ndn/ch/unibas/foo1", "unibas-foo1")
        c2 = Content("/ndn/ch/unibas/foo2", "unibas-foo2")
        c3 = Content("/ndn/ch/unibas/foo/bar1", "unibas-foo-bar1")
        c4 = Content("/ndn/ch/unibas/foo3", "unibas-foo3")
        c5 = Content("/ndn/ch/unibas/foo/bar2", "unibas-foo-bar2")
        c6 = Content("/ndn/ch/unibas/foo4", "unibas-foo4")
        c7 = Content("/ndn/ch", "ndn-ch")
        # insert
        self.tree.insert(c1)
        self.tree.insert(c2)
        self.tree.insert(c3)
        self.tree.insert(c4)
        self.tree.insert(c5)
        self.tree.insert(c6)
        self.tree.insert(c7)
        # remove
        self.tree.remove(c2.name)
        self.tree.remove(c5.name)
        self.tree.remove(c7.name)
        # exact lookup
        self.assertEqual(self.tree.exact_lookup(c1.name), c1)
        self.assertEqual(self.tree.exact_lookup(c2.name), None)
        self.assertEqual(self.tree.exact_lookup(c3.name), c3)
        self.assertEqual(self.tree.exact_lookup(c4.name), c4)
        self.assertEqual(self.tree.exact_lookup(c5.name), None)
        self.assertEqual(self.tree.exact_lookup(c6.name), c6)
        self.assertEqual(self.tree.exact_lookup(c7.name), None)
        # insert again and lookup
        self.tree.insert(c2)
        self.tree.insert(c5)
        self.tree.insert(c7)
        self.assertEqual(self.tree.exact_lookup(c2.name), c2)
        self.assertEqual(self.tree.exact_lookup(c5.name), c5)
        self.assertEqual(self.tree.exact_lookup(c7.name), c7)

    def test_insert_remove_prefix_lookup(self):
        # create content objects
        c1 = Content("/ndn/ch/unibas/foo1", "unibas-foo1")
        c2 = Content("/ndn/ch/unibas/foo2", "unibas-foo2")
        c3 = Content("/ndn/ch/unibas/foo/bar1", "unibas-foo-bar1")
        c4 = Content("/ndn/ch/unibas/foo3", "unibas-foo3")
        c5 = Content("/ndn/ch/unibas/foo/bar2", "unibas-foo-bar2")
        c6 = Content("/ndn/ch/unibas/foo4", "unibas-foo4")
        c7 = Content("/ndn/ch", "ndn-ch")

        # insert
        self.tree.insert(c1)
        self.tree.insert(c2)
        self.tree.insert(c3)
        self.tree.insert(c4)
        self.tree.insert(c5)
        self.tree.insert(c6)
        self.tree.insert(c7)

        # prefix lookup
        n1 = self.tree.prefix_lookup(Name("/ndn")).name
        self.assertTrue(Name("/ndn").is_prefix_of(n1))

        n2 = self.tree.prefix_lookup(Name("/ndn/ch")).name
        self.assertTrue(Name("/ndn/ch").is_prefix_of(n2))

        n3 = self.tree.prefix_lookup(Name("/ndn/ch/unibas")).name
        self.assertTrue(Name("/ndn/ch/unibas").is_prefix_of(n3))

        n4 = self.tree.prefix_lookup(Name("/ndn/ch/unibas/foo1")).name
        self.assertTrue(Name("/ndn/ch/unibas/foo1").is_prefix_of(n4))

        n5 = self.tree.prefix_lookup(Name("/ndn/ch/unibas/foo/bar1")).name
        self.assertTrue(Name("/ndn/ch/unibas/foo/bar1").is_prefix_of(n5))

        self.assertEqual(self.tree.prefix_lookup(Name("/unknown")), None)
        self.assertEqual(self.tree.prefix_lookup(Name("/ndn/unknown")), None)
        self.assertEqual(self.tree.prefix_lookup(Name("/ndn/ch/unknown")), None)
        self.assertEqual(self.tree.prefix_lookup(Name("/ndn/ch/foo1/unknown")), None)

        # remove
        self.tree.remove(c1.name)

        # prefix lookup
        n1 = self.tree.prefix_lookup(Name("/ndn")).name
        self.assertTrue(Name("/ndn").is_prefix_of(n1))

        n2 = self.tree.prefix_lookup(Name("/ndn/ch")).name
        self.assertTrue(Name("/ndn/ch").is_prefix_of(n2))
