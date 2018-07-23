
import unittest

import multiprocessing
import queue
from datetime import datetime, timedelta
from time import sleep

from PiCN.Layers.LinkLayer import BasicLinkLayer
from PiCN.Layers.LinkLayer.FaceIDTable import FaceIDDict
from PiCN.Layers.LinkLayer.Interfaces import AddressInfo
from PiCN.Layers.RoutingLayer import BasicRoutingLayer
from PiCN.Layers.RoutingLayer.RoutingInformationBase import BaseRoutingInformationBase, TreeRoutingInformationBase
from PiCN.Layers.ICNLayer.ForwardingInformationBase import BaseForwardingInformationBase, \
    ForwardingInformationBaseMemoryPrefix
from PiCN.Layers.RoutingLayer.test.mocks import MockInterface
from PiCN.Packets import Interest, Content, Name
from PiCN.Processes import PiCNSyncDataStructFactory


class test_RoutingLayer(unittest.TestCase):

    def setUp(self):
        synced_data_struct_factory = PiCNSyncDataStructFactory()
        synced_data_struct_factory.register('fib', ForwardingInformationBaseMemoryPrefix)
        synced_data_struct_factory.register('rib', TreeRoutingInformationBase)
        synced_data_struct_factory.register('faceidtable', FaceIDDict)
        synced_data_struct_factory.create_manager()

        self.mock_interface = MockInterface(0)
        self.fidtable = synced_data_struct_factory.manager.faceidtable()
        self.linklayer = BasicLinkLayer([self.mock_interface], self.fidtable)
        self.peer = ('127.42.13.37', 6363)

        self.fib: BaseForwardingInformationBase = synced_data_struct_factory.manager.fib()
        self.rib: BaseRoutingInformationBase = synced_data_struct_factory.manager.rib()

        self.routinglayer = BasicRoutingLayer(self.linklayer, [self.peer])

        self.routinglayer.rib = self.rib
        self.routinglayer.fib = self.fib
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
        self.rib.insert(Name('/ndn/ch/unibas'), 42, 3)

        self.routinglayer.start_process()
        waittime = 1.0

        # The routing interest sent into the layer
        i = Interest(Name('/routing'))
        # The expected reply - a content packet with empty content
        c = Content(Name('/routing'), '/ndn/ch/unibas:3:-1\n'.encode('utf-8'))
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
        announcement = Content(Name('/routing'), '/ndn/ch/unibas:3:-1\n'.encode('utf-8'))
        # Make sure an interest for /routing is sent out
        try:
            self.queue_to_lower.get(timeout=waittime)
        except queue.Empty:
            self.fail()
        # Send the route announcement, then wait for a moment
        self.queue_from_lower.put([42, announcement])
        sleep(waittime)
        # Make sure an appropriate entry is added to the RIB (with incremented distance)
        for name, fid, dist, _ in self.rib.entries():
            if name == Name('/ndn/ch/unibas') and fid == 42 and dist == 4:
                return
        self.fail()

    def test_ageing(self):
        waittime: float = 3.0
        peerfid = self.linklayer.faceidtable.get_or_create_faceid(AddressInfo(self.peer, 0))
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
