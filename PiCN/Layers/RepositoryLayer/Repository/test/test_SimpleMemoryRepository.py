"""Test the Simple File System Repository"""

import unittest
import multiprocessing

from PiCN.Layers.RepositoryLayer.Repository import SimpleMemoryRepository
from PiCN.Packets import Content, Name


class test_SimpleMemoryRepository(unittest.TestCase):
    """Test the Simple Memory Repository"""

    def setUp(self):
        manager = multiprocessing.Manager()
        self.repository = SimpleMemoryRepository(Name('/test/data'), manager=manager)
        self.repository._storage[Name('/test/data/f1')] = 'data1'
        self.repository._storage[Name('/test/data/f2')] = 'data2'
        self.repository._storage[Name('/test/data/f3')] = 'data3'

    def test_content_available(self):
        """Test if the function is_content_available works correct"""
        del self.repository._storage[Name('/test/data/f3')]
        self.assertTrue(self.repository.is_content_available(Name("/test/data/f1")))
        self.assertTrue(self.repository.is_content_available(Name("/test/data/f2")))
        self.assertFalse(self.repository.is_content_available(Name("/test/data/f3")))

    def test_get_content(self):
        """test if the function get content works correct"""
        del self.repository._storage[Name('/test/data/f3')]
        c1_cmp = Content("/test/data/f1", "data1")
        c1 = self.repository.get_content(Name("/test/data/f1"))
        self.assertEqual(c1, c1_cmp)

        c2_cmp = Content("/test/data/f2", "data2")
        c2 = self.repository.get_content(Name("/test/data/f2"))
        self.assertEqual(c2, c2_cmp)

        c3 = self.repository.get_content(Name("/test/data/f3"))
        self.assertEqual(c3, None)

    def test_get_content_invalid_prefix(self):
        """test if the function get content do not return data from a invalid prefix"""
        c10 = self.repository.get_content(Name("/data/test/f1"))
        self.assertEqual(c10, None)

    def test_add_content(self):
        name = Name('/test/data/f4')
        self.assertFalse(self.repository.is_content_available(name))
        self.repository.add_content(name, 'data4')
        c4_cmp = Content(name, 'data4')
        self.assertTrue(self.repository.is_content_available(name))
        self.assertEqual(c4_cmp, self.repository.get_content(name))

    def test_remove_content(self):
        name2 = Name('/test/data/f2')
        name3 = Name('/test/data/f3')
        self.assertTrue(self.repository.is_content_available(name2))
        self.assertTrue(self.repository.is_content_available(name3))
        self.repository.remove_content(name3)
        self.assertTrue(self.repository.is_content_available(name2))
        self.assertFalse(self.repository.is_content_available(name3))
