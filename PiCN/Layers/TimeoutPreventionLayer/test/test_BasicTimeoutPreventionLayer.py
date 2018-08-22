"""Tests of the BasicR2CLayer"""

import time
import unittest
import multiprocessing

from PiCN.Layers.TimeoutPreventionLayer import BasicTimeoutPreventionLayer, TimeoutPreventionMessageDict
from PiCN.Layers.NFNLayer.NFNComputationTable import NFNComputationList
from PiCN.Packets import Interest, Content, Nack, NackReason
from PiCN.Processes import PiCNSyncDataStructFactory

class test_BasicTimeoutPreventionLayer(unittest.TestCase):
    """Tests of the BasicR2CLayer"""

    def setUp(self):
        synced_data_struct_factory = PiCNSyncDataStructFactory()
        synced_data_struct_factory.register("timeoutPreventionMessageDict", TimeoutPreventionMessageDict)
        synced_data_struct_factory.register("NFNComputationList", NFNComputationList)
        synced_data_struct_factory.create_manager()

        tpmd = synced_data_struct_factory.manager.timeoutPreventionMessageDict()
        nfncl = synced_data_struct_factory.manager.NFNComputationList(None, None)

        self.timeoutPreventionLayer = BasicTimeoutPreventionLayer(tpmd, nfncl)
        self.timeoutPreventionLayer.queue_from_higher = multiprocessing.Queue()
        self.timeoutPreventionLayer.queue_from_lower = multiprocessing.Queue()
        self.timeoutPreventionLayer.queue_to_higher = multiprocessing.Queue()
        self.timeoutPreventionLayer.queue_to_lower = multiprocessing.Queue()
        self.timeoutPreventionLayer.start_process()

    def tearDown(self):
        self.timeoutPreventionLayer.stop_process()


    def test_interest_from_lower(self):
        """test that an interest from lower is directly forwarded to upper"""
        interest =  Interest("/test/data")
        self.timeoutPreventionLayer.queue_from_lower.put([1, interest])
        res = self.timeoutPreventionLayer.queue_to_higher.get(timeout=2.0)
        self.assertEqual([1, interest], res)

    def test_interest_from_higher(self):
        """test sending an interest from higher without adding it to the dict"""
        interest = Interest("/test/data")
        self.timeoutPreventionLayer.queue_from_higher.put([1, interest])
        res = self.timeoutPreventionLayer.queue_to_lower.get(timeout=2.0)
        self.assertEqual([1, interest], res)
        e = self.timeoutPreventionLayer.message_dict.get_entry(interest.name)
        self.assertTrue(e is None)

    def test_nfn_interest_from_higher(self):
        """test sending an interest from higher and adding it to the dict"""
        interest = Interest("/test/func()/NFN")
        self.timeoutPreventionLayer.queue_from_higher.put([1, interest])
        res = self.timeoutPreventionLayer.queue_to_lower.get(timeout=2.0)
        self.assertEqual([1, interest], res)
        e = self.timeoutPreventionLayer.message_dict.get_entry(interest.name)
        self.assertTrue(e is not None)

    def test_content_from_lower_no_message_dict_entry(self):
        """test content from lower with no message dict entry"""
        content = Content("/test/data")
        self.timeoutPreventionLayer.queue_from_lower.put([1, content])
        res = self.timeoutPreventionLayer.queue_to_higher.get(timeout=2.0)
        self.assertEqual([1, content], res)
        e = self.timeoutPreventionLayer.message_dict.get_entry(content.name)
        self.assertTrue(e is None)

    def test_content_from_lower_message_dict_entry(self):
        """test content from lower with message dict entry"""
        content = Content("/test/data")
        self.timeoutPreventionLayer.message_dict.create_entry(content.name)
        e = self.timeoutPreventionLayer.message_dict.get_entry(content.name)
        self.assertTrue(e is not None)
        self.timeoutPreventionLayer.queue_from_lower.put([1, content])
        res = self.timeoutPreventionLayer.queue_to_higher.get(timeout=2.0)
        self.assertEqual([1, content], res)
        e = self.timeoutPreventionLayer.message_dict.get_entry(content.name)
        self.assertTrue(e is None)

    def test_content_from_higher(self):
        """test content from higher"""
        content = Content("/test/data")
        self.timeoutPreventionLayer.queue_from_higher.put([1, content])
        res = self.timeoutPreventionLayer.queue_to_lower.get(timeout=2.0)
        self.assertEqual([1, content], res)

    def test_nack_from_lower_message_dict_entry(self):
        """test nack from lower WITH message dict entry"""
        nack = Nack("/test/data", interest=Interest("/test/data"), reason=NackReason.CONGESTION)
        self.timeoutPreventionLayer.message_dict.create_entry(nack.name)
        e = self.timeoutPreventionLayer.message_dict.get_entry(nack.name)
        self.assertTrue(e is not None)
        self.timeoutPreventionLayer.queue_from_lower.put([1, nack])
        res = self.timeoutPreventionLayer.queue_to_higher.get(timeout=2.0)
        self.assertEqual([1, nack], res)
        e = self.timeoutPreventionLayer.message_dict.get_entry(nack.name)
        self.assertTrue(e is None)

    def test_nack_from_higher(self):
        """test nack from higher """
        nack = Nack("/test/data", interest=Interest("/test/data"), reason=NackReason.CONGESTION)
        self.timeoutPreventionLayer.queue_from_higher.put([1, nack])
        res = self.timeoutPreventionLayer.queue_to_lower.get(timeout=2.0)
        self.assertEqual([1, nack], res)

    def test_keepalive_from_lower_message_dict_entry(self):
        """test r2c from lower with message dict entry"""
        content = Content("/test/data/_()/KEEPALIVE/NFN")
        self.timeoutPreventionLayer.message_dict.create_entry(content.name)
        e1 = self.timeoutPreventionLayer.message_dict.get_entry(content.name)
        ts = e1.timestamp
        self.assertTrue(e1 is not None)
        self.timeoutPreventionLayer.queue_from_lower.put([1, content])
        time.sleep(1.0)
        e2 = self.timeoutPreventionLayer.message_dict.get_entry(content.name)
        self.assertTrue(e2 is not None)
        self.assertTrue(e2.timestamp > ts)

    def test_keep_alive_ageing_no_reply(self):
        """test ageing with keepalive with no keep alive reply"""
        self.timeoutPreventionLayer.ageing()

        interest = Interest("/test/func/_()/NFN")
        keepalive = Interest("/test/func/_()/KEEPALIVE/NFN")
        self.timeoutPreventionLayer.queue_from_higher.put([1, interest])

        res1 = self.timeoutPreventionLayer.queue_to_lower.get(timeout=2.0)
        self.assertEqual(res1, [1, interest])
        e1 = self.timeoutPreventionLayer.message_dict.get_entry(interest.name)
        self.assertTrue(e1 is not None)
        e2 = self.timeoutPreventionLayer.message_dict.get_entry(keepalive.name)
        self.assertTrue(e2 is not None)

        res2 = self.timeoutPreventionLayer.queue_to_lower.get(timeout=2.0)
        self.assertEqual(res2, [-1, interest])

        res3 = self.timeoutPreventionLayer.queue_to_lower.get(timeout=2.0)
        self.assertEqual(res3, [-1, keepalive])

        res4 = self.timeoutPreventionLayer.queue_to_lower.get(timeout=2.0)
        self.assertEqual(res4, [-1, interest])

        res5 = self.timeoutPreventionLayer.queue_to_lower.get(timeout=2.0)
        self.assertEqual(res5, [-1, keepalive])

        res6 = self.timeoutPreventionLayer.queue_to_lower.get(timeout=2.0)
        self.assertEqual(res6, [-1, interest])

        self.assertTrue(self.timeoutPreventionLayer.queue_to_lower.empty())

        res7 = self.timeoutPreventionLayer.queue_to_higher.get(timeout=2.0)
        self.assertEqual(res7, [-1, Nack(name=interest.name, reason=NackReason.NOT_SET, interest=interest)])

    def test_keep_alive_ageing_reply(self):
        """test ageing with keepalive with no keep alive reply"""
        self.timeoutPreventionLayer.ageing()

        interest = Interest("/test/func/_()/NFN")
        content = Content(interest.name, "data")
        keepalive = Interest("/test/func/_()/KEEPALIVE/NFN")
        keepalive_rely = Content(keepalive.name, "")

        self.timeoutPreventionLayer.queue_from_higher.put([1, interest])

        res1 = self.timeoutPreventionLayer.queue_to_lower.get(timeout=2.0)
        self.assertEqual(res1, [1, interest])
        e1 = self.timeoutPreventionLayer.message_dict.get_entry(interest.name)
        self.assertTrue(e1 is not None)
        e2 = self.timeoutPreventionLayer.message_dict.get_entry(keepalive.name)
        self.assertTrue(e2 is not None)

        res2 = self.timeoutPreventionLayer.queue_to_lower.get(timeout=2.0)
        self.assertEqual(res2, [-1, interest])

        res3 = self.timeoutPreventionLayer.queue_to_lower.get(timeout=2.0)
        self.assertEqual(res3, [-1, keepalive])

        self.timeoutPreventionLayer.queue_from_lower.put([4, keepalive_rely])
        e1 = self.timeoutPreventionLayer.message_dict.get_entry(interest.name)
        self.assertTrue(e1 is not None)
        e2 = self.timeoutPreventionLayer.message_dict.get_entry(keepalive.name)
        self.assertTrue(e2 is not None)

        res4 = self.timeoutPreventionLayer.queue_to_lower.get(timeout=2.0)
        self.assertEqual(res4, [-1, interest])

        res5 = self.timeoutPreventionLayer.queue_to_lower.get(timeout=2.0)
        self.assertEqual(res5, [-1, keepalive])


        self.timeoutPreventionLayer.queue_from_lower.put([4, keepalive_rely])
        e1 = self.timeoutPreventionLayer.message_dict.get_entry(interest.name)
        self.assertTrue(e1 is not None)
        e2 = self.timeoutPreventionLayer.message_dict.get_entry(keepalive.name)
        self.assertTrue(e2 is not None)

        res6 = self.timeoutPreventionLayer.queue_to_lower.get(timeout=2.0)
        self.assertEqual(res6, [-1, interest])

        res7 = self.timeoutPreventionLayer.queue_to_lower.get(timeout=2.0)
        self.assertEqual(res7, [-1, keepalive])

        self.timeoutPreventionLayer.queue_from_lower.put([4, keepalive_rely])

        res8 = self.timeoutPreventionLayer.queue_to_lower.get(timeout=2.0)
        self.assertEqual(res8, [-1, interest])

        res9 = self.timeoutPreventionLayer.queue_to_lower.get(timeout=2.0)
        self.assertEqual(res9, [-1, keepalive])

        self.timeoutPreventionLayer.queue_from_lower.put([5, content])

        time.sleep(1)
        e1 = self.timeoutPreventionLayer.message_dict.get_entry(interest.name)
        self.assertTrue(e1 is None)
        e2 = self.timeoutPreventionLayer.message_dict.get_entry(keepalive.name)
        self.assertTrue(e2 is None)
        self.assertEqual(len(self.timeoutPreventionLayer.message_dict.get_container()), 0)

        res = self.timeoutPreventionLayer.queue_to_higher.get(timeout=2.0)
        self.assertEqual(res, [5, content])
        self.assertTrue(self.timeoutPreventionLayer.queue_to_lower.empty())


    def test_keep_alive_request(self):
        """test replying a incoming keep alive request"""
        interest = Interest("/test/func/_()/NFN")
        keep_alive = Interest("/test/func/_()/KEEPALIVE/NFN")
        content = Content(keep_alive.name)

        self.timeoutPreventionLayer.nfn_comp_table.add_computation(interest.name, 3, interest)

        self.timeoutPreventionLayer.queue_from_lower.put([3, keep_alive])
        self.assertTrue(self.timeoutPreventionLayer.queue_to_higher.empty())
        res = self.timeoutPreventionLayer.queue_to_lower.get(timeout=2.0)
        self.assertEqual(res, [3, content])

    def test_keep_alive_request_no_comp_running(self):
        """test replying a incoming keep alive request if no comp running"""
        keep_alive = Interest("/test/func/_()/KEEPALIVE/NFN")
        nack = Nack(keep_alive.name, reason=NackReason.COMP_NOT_RUNNING, interest=keep_alive)

        self.timeoutPreventionLayer.queue_from_lower.put([3, keep_alive])
        self.assertTrue(self.timeoutPreventionLayer.queue_to_higher.empty())
        res = self.timeoutPreventionLayer.queue_to_lower.get(timeout=2.0)
        self.assertEqual(res, [3, nack])
