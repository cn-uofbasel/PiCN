"""Tests of the BasicR2CLayer"""

import unittest
import multiprocessing

from PiCN.Layers.TimeoutPreventionLayer import BasicTimeoutPreventionLayer, TimeoutPreventionMessageDict
from PiCN.Packets import Interest
from PiCN.Processes import PiCNSyncDataStructFactory

class test_BasicTimeoutPreventionLayer(unittest.TestCase):
    """Tests of the BasicR2CLayer"""

    def setUp(self):
        synced_data_struct_factory = PiCNSyncDataStructFactory()
        synced_data_struct_factory.register("timeoutPreventionMessageDict", TimeoutPreventionMessageDict)
        synced_data_struct_factory.create_manager()

        tpmd = synced_data_struct_factory.manager.timeoutPreventionMessageDict()

        self.timeoutPreventionLayer = BasicTimeoutPreventionLayer(tpmd)
        self.timeoutPreventionLayer.queue_from_higher = multiprocessing.Queue()
        self.timeoutPreventionLayer.queue_from_lower = multiprocessing.Queue()
        self.timeoutPreventionLayer.queue_to_higher = multiprocessing.Queue()
        self.timeoutPreventionLayer.queue_to_lower = multiprocessing.Queue()
        self.timeoutPreventionLayer.start_process()

    def tearDown(self):
        self.timeoutPreventionLayer.stop_process()


    def test_interest_from_lower(self):
        interest =  Interest("/test/data")
        self.timeoutPreventionLayer.queue_from_lower.put([1, interest])
        res = self.timeoutPreventionLayer.queue_to_higher.get()

        self.assertEqual([1, interest], res)