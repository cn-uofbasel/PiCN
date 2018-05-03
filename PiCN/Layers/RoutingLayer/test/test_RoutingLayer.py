
import unittest

import multiprocessing
import queue
from datetime import datetime, timedelta
from time import sleep

from PiCN.Layers.RoutingLayer import BasicRoutingLayer
from PiCN.Layers.RoutingLayer.RoutingInformationBase import BaseRoutingInformationBase, TreeRoutingInformationBase
from PiCN.Layers.ICNLayer.ForwardingInformationBase import BaseForwardingInformationBase, \
    ForwardingInformationBaseMemoryPrefix
from PiCN.Layers.RoutingLayer.test.mocks import MockLinkLayer
from PiCN.Packets import Interest, Content, Name


class test_RoutingLayer(unittest.TestCase):

    def setUp(self):
        self.linklayer_mock = MockLinkLayer()
        self.peer = ('127.42.13.37', 6363)

        self.data_structs = multiprocessing.Manager().dict()
        self.data_structs['fib']: BaseForwardingInformationBase = ForwardingInformationBaseMemoryPrefix()
        self.data_structs['rib']: BaseRoutingInformationBase = TreeRoutingInformationBase()

        self.routinglayer = BasicRoutingLayer(self.linklayer_mock, self.data_structs, [self.peer])

        self.routinglayer.queue_to_higher = self.queue_to_higher = multiprocessing.Queue()
        self.routinglayer.queue_from_higher = self.queue_from_higher = multiprocessing.Queue()
        self.routinglayer.queue_to_lower = self.queue_to_lower = multiprocessing.Queue()
        self.routinglayer.queue_from_lower = self.queue_from_lower = multiprocessing.Queue()

    def tearDown(self):
        self.routinglayer.stop_process()

    def test_pass_through(self):
        """
        Test that routing-unrelated packets are passed through without change.
        """
        self.routinglayer.start_process()
        waittime = 1.0

        # Test lower-to-higher pass-through
        i1 = Interest(Name('/test1'))
        self.queue_from_lower.put([42, i1])
        # Collect all packets for a short time
        timeout = datetime.utcnow() + timedelta(seconds=waittime)
        packets = []
        while datetime.utcnow() < timeout:
            try:
                packets.append(self.queue_to_higher.get(timeout=waittime/10))
            except queue.Empty:
                pass
        # Test for exactly one occurrence of the wanted packet
        self.assertIn([42, i1], packets)
        packets.remove([42, i1])
        self.assertNotIn([42, i1], packets)

        # Test lower-to-higher pass-through
        i2 = Interest(Name('/test2'))
        self.queue_from_higher.put([1337, i2])
        # Collect all packets for a short time
        timeout = datetime.utcnow() + timedelta(seconds=waittime)
        packets = []
        while datetime.utcnow() < timeout:
            try:
                packets.append(self.queue_to_lower.get(timeout=waittime/10))
            except queue.Empty:
                pass
        # Test for exactly one occurrence of the wanted packet
        self.assertIn([1337, i2], packets)
        packets.remove([1337, i2])
        self.assertNotIn([1337, i2], packets)

    def test_empty_routing_content(self):
        """
        Test that an empty /routing content packet is sent in reply to a /routing interest.
        """
        self.routinglayer.start_process()
        waittime = 1.0

        # The routing interest sent into the layer
        i = Interest(Name('/routing'))
        # The expected reply - a content packet with empty content
        c = Content(Name('/routing'), bytes())
        self.queue_from_lower.put([42, i])
        # Collect all packets for a short time
        timeout = datetime.utcnow() + timedelta(seconds=waittime)
        packets = []
        while datetime.utcnow() < timeout:
            try:
                packets.append(self.queue_to_lower.get(timeout=waittime/10))
            except queue.Empty:
                pass
        # Test for exactly one occurrence of the wanted packet
        self.assertIn([42, c], packets)
        packets.remove([42, c])
        self.assertNotIn([42, c], packets)

    def test_nonempty_routing_content(self):
        rib: BaseRoutingInformationBase = self.data_structs['rib']
        rib.insert(Name('/ndn/ch/unibas'), 42, 3)
        self.data_structs['rib'] = rib

        self.routinglayer.start_process()
        waittime = 1.0

        # The routing interest sent into the layer
        i = Interest(Name('/routing'))
        # The expected reply - a content packet with empty content
        c = Content(Name('/routing'), '/ndn/ch/unibas:3\n'.encode('utf-8'))
        self.queue_from_lower.put([42, i])
        # Collect all packets for a short time
        timeout = datetime.utcnow() + timedelta(seconds=waittime)
        packets = []
        while datetime.utcnow() < timeout:
            try:
                packets.append(self.queue_to_lower.get(timeout=waittime/10))
            except queue.Empty:
                pass
        # Test for exactly one occurrence of the wanted packet
        self.assertIn([42, c], packets)
        packets.remove([42, c])
        self.assertNotIn([42, c], packets)

    def test_add_to_rib(self):
        """
        Test that an arriving routing packet is processed properly by inserting the announced routes into the RIB.
        """
        self.routinglayer.start_process()
        waittime = 1.0

        # The packet containing the route announcements of the peer
        announcement = Content(Name('/routing'), '/ndn/ch/unibas:3\n'.encode('utf-8'))
        # Make sure an interest for /routing is sent out
        try:
            self.queue_to_lower.get(timeout=waittime)
        except queue.Empty:
            self.fail()
        # Send the route announcement, then wait for a moment
        self.queue_from_lower.put([42, announcement])
        sleep(waittime)
        # Make sure an appropriate entry is added to the RIB (with incremented distance)
        self.assertIn((Name('/ndn/ch/unibas'), 42, 4), self.data_structs['rib'])

    def test_ageing(self):
        waittime: float = 3.0
        peerfid = self.linklayer_mock._get_or_create_fid(self.peer, static=True)
        self.routinglayer._ageing_interval = 0.5

        self.routinglayer.start_process()

        # Collect all packets for a short time
        timeout = datetime.utcnow() + timedelta(seconds=waittime)
        packets = []
        while datetime.utcnow() < timeout:
            try:
                packets.append(self.queue_to_lower.get(timeout=waittime/10))
            except queue.Empty:
                pass
        filtered = [p for p in packets if p[0] == peerfid and p[1] == Interest(Name('/routing'))]
        self.assertGreater(len(filtered), 5)
