"""Tests for the in Memory Content Store with exact matching"""

import unittest

from PiCN.Layers.ICNLayer.ContentStore.ContentStoreMemoryExact import ContentStoreMemoryExact
from PiCN.Packets import Content


class test_ContentStoreMemoryExact(unittest.TestCase):

    def setUp(self):
        self.cs = ContentStoreMemoryExact()

    def tearDown(self):
        pass

    def test_add_content_to_cs(self):
        """Test adding data to CS"""
        c = Content("/test/data", "Hello World")
        self.cs.add_content_object(c)
        entry = self.cs._container[0]
        self.assertIsNotNone(self.cs.find_content_object(entry.name))
        self.assertEqual(entry.content, c)

    def test_add_multiple_content_to_cs(self):
        """Test adding multiple data to CS"""
        c1 = Content("/test/data", "Hello World")
        c2 = Content("/data/test", "Goodbye")
        self.cs.add_content_object(c1)
        self.cs.add_content_object(c2)
        entry1 = self.cs._container[0]
        self.assertIsNotNone(self.cs.find_content_object(entry1.name))
        self.assertEqual(entry1.content, c1)
        entry2 = self.cs._container[1]
        self.assertIsNotNone(self.cs.find_content_object(entry2.name))
        self.assertEqual(entry2.content, c2)

    def test_find_content_to_cs(self):
        """Test adding and searching data to CS"""
        c = Content("/test/data", "Hello World")
        self.cs.add_content_object(c)
        entry = self.cs._container[0].content
        self.assertEqual(entry, c)
        fc = self.cs.find_content_object(c.name)
        self.assertEqual(fc.content, c)

    def test_find_multiple_content_to_cs(self):
        """Test finding multiple data to CS"""
        c1 = Content("/test/data", "Hello World")
        c2 = Content("/data/test", "Goodbye")
        self.cs.add_content_object(c1)
        self.cs.add_content_object(c2)
        entry1 = self.cs._container[0]
        self.assertTrue(entry1 in self.cs.get_container())
        self.assertEqual(entry1.content, c1)
        entry2 = self.cs._container[1]
        self.assertTrue(entry2 in self.cs.get_container())
        self.assertEqual(entry2.content, c2)

        fc1 = self.cs.find_content_object(c1.name)
        self.assertEqual(fc1.content, c1)

        fc2 = self.cs.find_content_object(c2.name)
        self.assertEqual(fc2.content, c2)

    def test_find_content_to_cs_no_match(self):
        """Test adding and searching data to CS"""
        c1 = Content("/test/data", "Hello World")
        c2 = Content("/data/test", "Hello World")
        self.cs.add_content_object(c1)
        entry = self.cs._container[0].content
        self.assertEqual(entry, c1)
        fc = self.cs.find_content_object(c2.name)
        self.assertEqual(fc, None)

    def test_remove_content_from_cs(self):
        """Test adding and removing data from CS"""
        c = Content("/test/data", "Hello World")
        self.cs.add_content_object(c)
        entry = self.cs._container[0].content
        self.assertEqual(entry, c)
        self.assertEqual(len(self.cs.get_container()), 1)
        self.cs.remove_content_object(c.name)
        self.assertEqual(len(self.cs.get_container()), 0)

    def test_ageing_removes_expired_non_static(self):
        """Expired non-static CS entry is evicted by ageing()."""
        self.cs.set_cs_timeout(1)
        c = Content("/test/data", "Hello World")
        self.cs.add_content_object(c, static=False)
        entry = self.cs.find_content_object(c.name)
        entry.timestamp = 0.0
        self.cs.ageing()
        self.assertIsNone(self.cs.find_content_object(c.name))

    def test_ageing_keeps_static_despite_old_timestamp(self):
        """Static entries are never aged out."""
        self.cs.set_cs_timeout(1)
        c = Content("/test/static", "Keep me")
        self.cs.add_content_object(c, static=True)
        entry = self.cs.find_content_object(c.name)
        entry.timestamp = 0.0
        self.cs.ageing()
        self.assertIsNotNone(self.cs.find_content_object(c.name))

    def test_ageing_keeps_fresh_non_static(self):
        """Non-expired entries remain."""
        self.cs.set_cs_timeout(60)
        c = Content("/test/fresh", "Still good")
        self.cs.add_content_object(c, static=False)
        self.cs.ageing()
        self.assertIsNotNone(self.cs.find_content_object(c.name))
