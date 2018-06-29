"""Tests for the in Memory Content Store with exact matching"""

import unittest

from PiCN.Layers.ICNLayer.ContentStore.ContentStorePersistentExact import ContentStorePersistentExact
from PiCN.Packets import Content


class test_ContentStoreMemoryExact(unittest.TestCase):

    def setUp(self):
        self.cs = ContentStorePersistentExact()

    def tearDown(self):
        pass

    def test_find_content_to_cs(self):
        """Test adding and searching data to CS"""
        c = Content("/test/data", "Hello World")
        self.cs.add_content_object(c)
        fc = self.cs.find_content_object(c.name)
        self.assertEqual(fc.content, c)

    def test_find_content_to_cs_no_match(self):
        """Test adding and searching data to CS"""
        c1 = Content("/test/data", "Hello World")
        c2 = Content("/data/test", "Hello World")
        self.cs.add_content_object(c1)
        fc = self.cs.find_content_object(c2.name)
        self.assertEqual(fc, None)

    def test_remove_content_from_cs(self):
        """Test adding and removing data from CS"""
        c = Content("/test/data", "Hello World")
        self.cs.add_content_object(c)
        self.cs.remove_content_object(c.name)
        fc = self.cs.find_content_object(c.name)
        self.assertEqual(fc, None)

        def test_restored(self):
            """Test adding and searching data to CS"""
            c = Content("/test/data", "Hello World")
            self.cs.add_content_object(c)
            fc = self.cs.find_content_object(c.name)
            self.assertEqual(fc.content, c)
            # close and restore
            db_path = self.cs.db_path
            self.cs.close_cs()
            restored_cs = ContentStorePersistentExact(db_path=db_path)
            restored_content = restored_cs.find_content_object(c.name)
            self.assertEqual(restored_cs.content, c)
