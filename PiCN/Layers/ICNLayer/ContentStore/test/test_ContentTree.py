"""Tests for the ContentTree data structure"""

import unittest

from PiCN.Layers.ICNLayer.ContentStore.ContentTree import ContentTree, ContentStoreEntry
from PiCN.Packets import Content, Name


class test_ContentTree(unittest.TestCase):

    def setUp(self):
        self.tree1_co = ContentTree()  # for tests with objects of type Content
        self.tree_cse = ContentTree()  # for tests with objects of type ContentStoreEntry

    def tearDown(self):
        pass

    def test_empty_tree(self):
        n = Name("/does/not/exist")
        self.tree1_co.exact_lookup(n)
        self.tree1_co.remove(n)

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
        self.tree1_co.insert(c1)
        self.tree1_co.insert(c2)
        self.tree1_co.insert(c3)
        self.tree1_co.insert(c4)
        self.tree1_co.insert(c5)
        self.tree1_co.insert(c6)
        self.tree1_co.insert(c7)
        # exact lookup
        self.assertEqual(self.tree1_co.exact_lookup(c1.name), c1)
        self.assertEqual(self.tree1_co.exact_lookup(c2.name), c2)
        self.assertEqual(self.tree1_co.exact_lookup(c3.name), c3)
        self.assertEqual(self.tree1_co.exact_lookup(c4.name), c4)
        self.assertEqual(self.tree1_co.exact_lookup(c5.name), c5)
        self.assertEqual(self.tree1_co.exact_lookup(c6.name), c6)
        self.assertEqual(self.tree1_co.exact_lookup(c7.name), c7)
        self.assertEqual(self.tree1_co.exact_lookup(Name("/ndn")), None)
        self.assertEqual(self.tree1_co.exact_lookup(Name("/unknown")), None)
        self.assertEqual(self.tree1_co.exact_lookup(Name("/ndn/ch/unknown")), None)
        self.assertEqual(self.tree1_co.exact_lookup(Name("/ndn/ch/unibas/foo1/unknown")), None)

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
        self.tree1_co.insert(c1)
        self.tree1_co.insert(c2)
        self.tree1_co.insert(c3)
        self.tree1_co.insert(c4)
        self.tree1_co.insert(c5)
        self.tree1_co.insert(c6)
        self.tree1_co.insert(c7)
        # remove
        self.tree1_co.remove(c2.name)
        self.tree1_co.remove(c5.name)
        self.tree1_co.remove(c7.name)
        # exact lookup
        self.assertEqual(self.tree1_co.exact_lookup(c1.name), c1)
        self.assertEqual(self.tree1_co.exact_lookup(c2.name), None)
        self.assertEqual(self.tree1_co.exact_lookup(c3.name), c3)
        self.assertEqual(self.tree1_co.exact_lookup(c4.name), c4)
        self.assertEqual(self.tree1_co.exact_lookup(c5.name), None)
        self.assertEqual(self.tree1_co.exact_lookup(c6.name), c6)
        self.assertEqual(self.tree1_co.exact_lookup(c7.name), None)
        # insert again and lookup
        self.tree1_co.insert(c2)
        self.tree1_co.insert(c5)
        self.tree1_co.insert(c7)
        self.assertEqual(self.tree1_co.exact_lookup(c2.name), c2)
        self.assertEqual(self.tree1_co.exact_lookup(c5.name), c5)
        self.assertEqual(self.tree1_co.exact_lookup(c7.name), c7)

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
        self.tree1_co.insert(c1)
        self.tree1_co.insert(c2)
        self.tree1_co.insert(c3)
        self.tree1_co.insert(c4)
        self.tree1_co.insert(c5)
        self.tree1_co.insert(c6)
        self.tree1_co.insert(c7)

        # prefix lookup
        n1 = self.tree1_co.prefix_lookup(Name("/ndn")).name
        self.assertTrue(Name("/ndn").is_prefix_of(n1))

        n2 = self.tree1_co.prefix_lookup(Name("/ndn/ch")).name
        self.assertTrue(Name("/ndn/ch").is_prefix_of(n2))

        n3 = self.tree1_co.prefix_lookup(Name("/ndn/ch/unibas")).name
        self.assertTrue(Name("/ndn/ch/unibas").is_prefix_of(n3))

        n4 = self.tree1_co.prefix_lookup(Name("/ndn/ch/unibas/foo1")).name
        self.assertTrue(Name("/ndn/ch/unibas/foo1").is_prefix_of(n4))

        n5 = self.tree1_co.prefix_lookup(Name("/ndn/ch/unibas/foo/bar1")).name
        self.assertTrue(Name("/ndn/ch/unibas/foo/bar1").is_prefix_of(n5))

        self.assertEqual(self.tree1_co.prefix_lookup(Name("/unknown")), None)
        self.assertEqual(self.tree1_co.prefix_lookup(Name("/ndn/unknown")), None)
        self.assertEqual(self.tree1_co.prefix_lookup(Name("/ndn/ch/unknown")), None)
        self.assertEqual(self.tree1_co.prefix_lookup(Name("/ndn/ch/foo1/unknown")), None)

        # remove
        self.tree1_co.remove(c1.name)

        # prefix lookup
        n1 = self.tree1_co.prefix_lookup(Name("/ndn")).name
        self.assertTrue(Name("/ndn").is_prefix_of(n1))

        n2 = self.tree1_co.prefix_lookup(Name("/ndn/ch")).name
        self.assertTrue(Name("/ndn/ch").is_prefix_of(n2))


    #################### Same Tests with objects of type ContentStoreEntry instead of Content ####################


    def test_cse_empty_tree(self):
        n = Name("/does/not/exist")
        self.tree_cse.exact_lookup(n)
        self.tree_cse.remove(n)

    def test_cse_insert_and_exact_lookup(self):
        # create objects of type ContentStoreEntry
        cse1 = ContentStoreEntry(Content("/ndn/ch/unibas/foo1", "unibas-foo1"))
        cse2 = ContentStoreEntry(Content("/ndn/ch/unibas/foo2", "unibas-foo2"))
        cse3 = ContentStoreEntry(Content("/ndn/ch/unibas/foo/bar1", "unibas-foo-bar1"))
        cse4 = ContentStoreEntry(Content("/ndn/ch/unibas/foo3", "unibas-foo3"))
        cse5 = ContentStoreEntry(Content("/ndn/ch/unibas/foo/bar2", "unibas-foo-bar2"))
        cse6 = ContentStoreEntry(Content("/ndn/ch/unibas/foo4", "unibas-foo4"))
        cse7 = ContentStoreEntry(Content("/ndn/ch", "ndn-ch"))
        # insert
        self.tree_cse.insert(cse1)
        self.tree_cse.insert(cse2)
        self.tree_cse.insert(cse3)
        self.tree_cse.insert(cse4)
        self.tree_cse.insert(cse5)
        self.tree_cse.insert(cse6)
        self.tree_cse.insert(cse7)
        # exact lookup
        self.assertEqual(self.tree_cse.exact_lookup(cse1.name), cse1)
        self.assertEqual(self.tree_cse.exact_lookup(cse2.name), cse2)
        self.assertEqual(self.tree_cse.exact_lookup(cse3.name), cse3)
        self.assertEqual(self.tree_cse.exact_lookup(cse4.name), cse4)
        self.assertEqual(self.tree_cse.exact_lookup(cse5.name), cse5)
        self.assertEqual(self.tree_cse.exact_lookup(cse6.name), cse6)
        self.assertEqual(self.tree_cse.exact_lookup(cse7.name), cse7)
        self.assertEqual(self.tree_cse.exact_lookup(Name("/ndn")), None)
        self.assertEqual(self.tree_cse.exact_lookup(Name("/unknown")), None)
        self.assertEqual(self.tree_cse.exact_lookup(Name("/ndn/ch/unknown")), None)
        self.assertEqual(self.tree_cse.exact_lookup(Name("/ndn/ch/unibas/foo1/unknown")), None)

    def test_cse_insert_remove_exact_lookup(self):
        # create objects of type ContentStoreEntry
        cse1 = ContentStoreEntry(Content("/ndn/ch/unibas/foo1", "unibas-foo1"))
        cse2 = ContentStoreEntry(Content("/ndn/ch/unibas/foo2", "unibas-foo2"))
        cse3 = ContentStoreEntry(Content("/ndn/ch/unibas/foo/bar1", "unibas-foo-bar1"))
        cse4 = ContentStoreEntry(Content("/ndn/ch/unibas/foo3", "unibas-foo3"))
        cse5 = ContentStoreEntry(Content("/ndn/ch/unibas/foo/bar2", "unibas-foo-bar2"))
        cse6 = ContentStoreEntry(Content("/ndn/ch/unibas/foo4", "unibas-foo4"))
        cse7 = ContentStoreEntry(Content("/ndn/ch", "ndn-ch"))
        # insert
        self.tree_cse.insert(cse1)
        self.tree_cse.insert(cse2)
        self.tree_cse.insert(cse3)
        self.tree_cse.insert(cse4)
        self.tree_cse.insert(cse5)
        self.tree_cse.insert(cse6)
        self.tree_cse.insert(cse7)
        # remove
        self.tree_cse.remove(cse2.name)
        self.tree_cse.remove(cse5.name)
        self.tree_cse.remove(cse7.name)
        # exact lookup
        self.assertEqual(self.tree_cse.exact_lookup(cse1.name), cse1)
        self.assertEqual(self.tree_cse.exact_lookup(cse2.name), None)
        self.assertEqual(self.tree_cse.exact_lookup(cse3.name), cse3)
        self.assertEqual(self.tree_cse.exact_lookup(cse4.name), cse4)
        self.assertEqual(self.tree_cse.exact_lookup(cse5.name), None)
        self.assertEqual(self.tree_cse.exact_lookup(cse6.name), cse6)
        self.assertEqual(self.tree_cse.exact_lookup(cse7.name), None)
        # insert again and lookup
        self.tree_cse.insert(cse2)
        self.tree_cse.insert(cse5)
        self.tree_cse.insert(cse7)
        self.assertEqual(self.tree_cse.exact_lookup(cse2.name), cse2)
        self.assertEqual(self.tree_cse.exact_lookup(cse5.name), cse5)
        self.assertEqual(self.tree_cse.exact_lookup(cse7.name), cse7)

    def test_cse_insert_remove_prefix_lookup(self):
        # create objects of type ContentStoreEntry
        cse1 = Content("/ndn/ch/unibas/foo1", "unibas-foo1")
        cse2 = Content("/ndn/ch/unibas/foo2", "unibas-foo2")
        cse3 = Content("/ndn/ch/unibas/foo/bar1", "unibas-foo-bar1")
        cse4 = Content("/ndn/ch/unibas/foo3", "unibas-foo3")
        cse5 = Content("/ndn/ch/unibas/foo/bar2", "unibas-foo-bar2")
        cse6 = Content("/ndn/ch/unibas/foo4", "unibas-foo4")
        cse7 = Content("/ndn/ch", "ndn-ch")

        # insert
        self.tree_cse.insert(cse1)
        self.tree_cse.insert(cse2)
        self.tree_cse.insert(cse3)
        self.tree_cse.insert(cse4)
        self.tree_cse.insert(cse5)
        self.tree_cse.insert(cse6)
        self.tree_cse.insert(cse7)

        # prefix lookup
        n1 = self.tree_cse.prefix_lookup(Name("/ndn")).name
        self.assertTrue(Name("/ndn").is_prefix_of(n1))

        n2 = self.tree_cse.prefix_lookup(Name("/ndn/ch")).name
        self.assertTrue(Name("/ndn/ch").is_prefix_of(n2))

        n3 = self.tree_cse.prefix_lookup(Name("/ndn/ch/unibas")).name
        self.assertTrue(Name("/ndn/ch/unibas").is_prefix_of(n3))

        n4 = self.tree_cse.prefix_lookup(Name("/ndn/ch/unibas/foo1")).name
        self.assertTrue(Name("/ndn/ch/unibas/foo1").is_prefix_of(n4))

        n5 = self.tree_cse.prefix_lookup(Name("/ndn/ch/unibas/foo/bar1")).name
        self.assertTrue(Name("/ndn/ch/unibas/foo/bar1").is_prefix_of(n5))

        self.assertEqual(self.tree_cse.prefix_lookup(Name("/unknown")), None)
        self.assertEqual(self.tree_cse.prefix_lookup(Name("/ndn/unknown")), None)
        self.assertEqual(self.tree_cse.prefix_lookup(Name("/ndn/ch/unknown")), None)
        self.assertEqual(self.tree_cse.prefix_lookup(Name("/ndn/ch/foo1/unknown")), None)

        # remove
        self.tree_cse.remove(cse1.name)

        # prefix lookup
        n1 = self.tree_cse.prefix_lookup(Name("/ndn")).name
        self.assertTrue(Name("/ndn").is_prefix_of(n1))

        n2 = self.tree_cse.prefix_lookup(Name("/ndn/ch")).name
        self.assertTrue(Name("/ndn/ch").is_prefix_of(n2))