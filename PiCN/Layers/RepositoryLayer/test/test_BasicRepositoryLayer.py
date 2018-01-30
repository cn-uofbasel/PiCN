"""Test the Basic Repository Layer"""

import multiprocessing
import os
import shutil
import unittest

from PiCN.Layers.RepositoryLayer import BasicRepositoryLayer

from PiCN.Layers.RepositoryLayer.Repository import SimpleFileSystemRepository
from PiCN.Packets import Content, Interest, Name, Nack


class test_BasicRepositoryLayer(unittest.TestCase):
    """Test the Basic Repository Layer"""

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
        self.repository = SimpleFileSystemRepository( self.path, Name("/test/data"))
        self.repositoryLayer = BasicRepositoryLayer(self.repository)

        self.q1_from_lower = multiprocessing.Queue()
        self.q1_to_lower = multiprocessing.Queue()

        self.repositoryLayer.queue_from_lower = self.q1_from_lower
        self.repositoryLayer.queue_to_lower = self.q1_to_lower

    def tearDown(self):
        try:
            shutil.rmtree( self.path)
            os.remove("/tmp/repo_unit_test")
        except:
            pass

    def test_requesting_content(self):
        """Test if content is correctly returned by Basic Repository Layer"""
        self.repositoryLayer.start_process()

        i1 = Interest("/test/data/f1")
        c1 = Content("/test/data/f1", "data1")
        self.repositoryLayer.queue_from_lower.put([0, i1])
        data = self.repositoryLayer.queue_to_lower.get()
        self.assertEqual(c1, data[1])

        i2 = Interest("/test/data/f2")
        c2 = Content("/test/data/f2", "data2")
        self.repositoryLayer.queue_from_lower.put([0, i2])
        data = self.repositoryLayer.queue_to_lower.get()
        self.assertEqual(c2, data[1])

    def test_nack_content(self):
        """Test if repo returns Nack if no matching content available"""
        self.repositoryLayer.start_process()
        i1 = Interest("/test/data/f3")
        n1 = Nack(i1.name, reason="No Matching Content")
        self.repositoryLayer.queue_from_lower.put([0, i1])
        data = self.repositoryLayer.queue_to_lower.get()
        self.assertEqual(n1, data[1])

    def test_nack_prefix(self):
        """Test if repo returns Nack if nprefix not matching"""
        self.repositoryLayer.start_process()
        i1 = Interest("/data/test/f1")
        n1 = Nack(i1.name, reason="No Matching Content")
        self.repositoryLayer.queue_from_lower.put([0, i1])
        data = self.repositoryLayer.queue_to_lower.get()
        self.assertEqual(n1, data[1])