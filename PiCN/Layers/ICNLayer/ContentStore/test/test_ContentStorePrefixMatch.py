"""Tests for ContentStorePrefixMatch"""

import unittest

from PiCN.Layers.ICNLayer.ContentStore.ContentStorePrefixMatch import ContentStorePrefixMatch
from PiCN.Packets import Content


class test_ContentStorePrefixMatch(unittest.TestCase):

    def setUp(self):
        self.cs = ContentStorePrefixMatch()

    def tearDown(self):
        pass

    def test_insert_and_lookup(self):
        # create content objects
        c1 = Content("/ndn/ch/unibas/foo1", "unibas-foo1")
        c2 = Content("/ndn/ch/unibas/foo2", "unibas-foo2")
        c3 = Content("/ndn/ch/unibas/foo/bar1", "unibas-foo-bar1")
        c4 = Content("/ndn/ch/unibas/foo3", "unibas-foo3")
        c5 = Content("/ndn/ch/unibas/foo/bar2", "unibas-foo-bar2")
        c6 = Content("/ndn/ch/unibas/foo4", "unibas-foo4")
        c7 = Content("/ndn/ch", "ndn-ch")
        # insert
        self.cs.add_content_object(c1)
        self.cs.add_content_object(c2)
        self.cs.add_content_object(c3)
        self.cs.add_content_object(c4)
        self.cs.add_content_object(c5)
        self.cs.add_content_object(c6)
        self.cs.add_content_object(c7)
        # lookup
        self.cs.find_content_object(c1.name).content.name.is_prefix_of(c1.name)
        self.cs.find_content_object(c2.name).content.name.is_prefix_of(c2.name)
        self.cs.find_content_object(c3.name).content.name.is_prefix_of(c3.name)
        self.cs.find_content_object(c4.name).content.name.is_prefix_of(c4.name)
        self.cs.find_content_object(c5.name).content.name.is_prefix_of(c5.name)
        self.cs.find_content_object(c6.name).content.name.is_prefix_of(c6.name)
        self.cs.find_content_object(c7.name).content.name.is_prefix_of(c7.name)