"""Test the ICN Flic Repository using fetch"""


import os
import shutil
import unittest
from random import randint

from PiCN.ProgramLibs.Fetch import Fetch

from PiCN.Packets import Name
from PiCN.ProgramLibs.ICNDataRepository import ICNFlicRepository


class test_ICNFlicRepository(unittest.TestCase):
    """Test the ICN Flic Repository using fetch"""
#TODO Write tests for FLIC, missing flic chunkifier

    def setUp(self):
        pass

    def tearDown(self):
        pass