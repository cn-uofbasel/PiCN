"""Test the Simple File System Repository"""

import os
import shutil
import unittest
import multiprocessing

from PiCN.Layers.RepositoryLayer.Repository import SimpleFileSystemRepository
from PiCN.Packets import Content, Name


class test_SimpleFileSystemRepository(unittest.TestCase):
    """Test the Simple File System Repository"""

    def setUp(self):
        self.path = "/tmp/repo_unit_test"
        try:
            os.stat( self.path)
        except:
            os.mkdir( self.path)
        with open( self.path + "/f1", 'w+') as content_file:
            content_file.write("data1")
        with open( self.path + "/f2", 'w+') as content_file:
            content_file.write("data2")
        with open("/tmp/f3", 'w+') as content_file:
            content_file.write("data3")
        manager = multiprocessing.Manager()
        self.repository = SimpleFileSystemRepository(self.path, Name("/test/data"), manager=manager)

    def tearDown(self):
        try:
            shutil.rmtree( self.path)
            os.remove("/tmp/repo_unit_test")
        except:
            pass


    def test_content_available(self):
        """Test if the function is_content_available works correct"""
        try:
            os.remove("/tmp/repo_unit_test/f3") #ensure there is no f3
        except:
            pass
        self.assertTrue(self.repository.is_content_available(Name("/test/data/f1")))
        self.assertTrue(self.repository.is_content_available(Name("/test/data/f2")))
        self.assertFalse(self.repository.is_content_available(Name("/test/data/f3")))

    def test_get_content(self):
        """test if the function get content works correct"""
        c1_cmp = Content("/test/data/f1", "data1")
        c1 = self.repository.get_content(Name("/test/data/f1"))
        self.assertEqual(c1, c1_cmp)

        c2_cmp = Content("/test/data/f2", "data2")
        c2 = self.repository.get_content(Name("/test/data/f2"))
        self.assertEqual(c2, c2_cmp)

        c3 = self.repository.get_content(Name("/test/data/f3"))
        self.assertEqual(c3, None)

    def test_get_content_directory_traversal(self):
        """test if the function get content do not allow directory traversal"""
        c4 = self.repository.get_content(Name("/test/data/../f3"))
        self.assertEqual(c4, None)

        c5 = self.repository.get_content(Name("/test/data/..%2Ff3"))
        self.assertEqual(c5, None)

        c6 = self.repository.get_content(Name("/test/data/..%2ff3"))
        self.assertEqual(c6, None)

        n1 = Name("/test/data")
        n1 += "../f3"
        c7 = self.repository.get_content(n1)
        self.assertEqual(c7, None)

        n2 = Name("/test/data")
        n2 += "..%2ff3"
        c8 = self.repository.get_content(n2)
        self.assertEqual(c8, None)

        n3 = Name("/test/data")
        n3 += "..%2Ff3"
        c9 = self.repository.get_content(n3)
        self.assertEqual(c9, None)

    def test_get_content_invalid_prefix(self):
        """test if the function get content do not return data from a invalid prefix"""
        c10 = self.repository.get_content(Name("/data/test/f1"))
        self.assertEqual(c10, None)


    def test_get_size(self):
        """test the functionality of the get size function"""
        c1 = self.repository.get_content(Name("/test/data/f1"))
        size = len(c1.content)
        self.assertEqual(size, self.repository.get_data_size(Name("/test/data/f1")))




