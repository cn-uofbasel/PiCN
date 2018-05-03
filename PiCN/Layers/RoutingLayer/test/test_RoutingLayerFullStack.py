
import unittest

import os
import shutil
import queue

from datetime import datetime, timedelta

from PiCN.Layers.PacketEncodingLayer.Encoder import NdnTlvEncoder
from PiCN.Layers.RoutingLayer.RoutingInformationBase import BaseRoutingInformationBase
from PiCN.Packets import Name
from PiCN.ProgramLibs.Fetch import Fetch
from PiCN.ProgramLibs.ICNDataRepository import ICNDataRepository
from PiCN.ProgramLibs.ICNForwarder import ICNForwarder


class test_RoutingLayerFullStack(unittest.TestCase):

    def setUp(self):
        self.f9000 = ICNForwarder(9000, encoder=NdnTlvEncoder(), routing=True,
                                  peers=[('127.0.0.1', 9001), ('127.0.0.1', 9002), ('127.0.0.1', 9090)])
        self.f9001 = ICNForwarder(9001, encoder=NdnTlvEncoder(), routing=True,
                                  peers=[('127.0.0.1', 9000), ('127.0.0.1', 9002), ('127.0.0.1', 9003),
                                         ('127.0.0.1', 9004)])
        self.f9002 = ICNForwarder(9002, encoder=NdnTlvEncoder(), routing=True,
                                  peers=[('127.0.0.1', 9000), ('127.0.0.1', 9001), ('127.0.0.1', 9004)])
        self.f9003 = ICNForwarder(9003, encoder=NdnTlvEncoder(), routing=True,
                                  peers=[('127.0.0.1', 9001), ('127.0.0.1', 9004)])
        self.f9004 = ICNForwarder(9004, encoder=NdnTlvEncoder(), routing=True,
                                  peers=[('127.0.0.1', 9001), ('127.0.0.1', 9002), ('127.0.0.1', 9003)])
        os.makedirs('/tmp/test_repo', exist_ok=True)
        f = open('/tmp/test_repo/helloworld', 'w')
        f.write('Hello, World!\n')
        f.close()
        self.repo = ICNDataRepository('/tmp/test_repo', Name('/testrepo'), port=9090, encoder=NdnTlvEncoder())
        self.fetch = Fetch('127.0.0.1', 9004, encoder=NdnTlvEncoder())
        # Create RIB entry for the repository (with Python weirdness)
        repo_fid: int = self.f9000.linklayer.create_new_fid(('127.0.0.1', 9090), static=True)
        rib: BaseRoutingInformationBase = self.f9000.data_structs['rib']
        rib.insert(Name('/testrepo'), repo_fid, distance=1, timeout=None)
        self.f9000.data_structs['rib'] = rib

    def tearDown(self):
        self.f9000.stop_forwarder()
        self.f9001.stop_forwarder()
        self.f9002.stop_forwarder()
        self.f9003.stop_forwarder()
        self.f9004.stop_forwarder()
        self.repo.stop_repo()
        self.fetch.stop_fetch()
        shutil.rmtree('/tmp/test_repo')

    def test_network(self):
        """
                C
                |
             F[9004] -- F[9003]
             /   \         /
            /     \       /
           /       \     /
        F[9002] -- F[9001]
            \        /
             \      /
              \    /
             F[9000]
                |
                R

        """
        self.f9000.start_forwarder()
        self.f9001.start_forwarder()
        self.f9002.start_forwarder()
        self.f9003.start_forwarder()
        self.f9004.start_forwarder()
        self.repo.start_repo()

        hw: str = ''
        until = datetime.utcnow() + timedelta(seconds=20)
        while hw != 'Hello, World!\n' and datetime.utcnow() < until:
            try:
                hw = self.fetch.fetch_data(Name('/testrepo/helloworld'), timeout=1.0)
            except queue.Empty:
                pass
        self.assertEqual('Hello, World!\n', hw)
        until = datetime.utcnow() + timedelta(seconds=20)
        hw = ''
        start = datetime.utcnow()
        end = start
        while hw != 'Hello, World!\n' and datetime.utcnow() < until:
            try:
                hw = self.fetch.fetch_data(Name('/testrepo/helloworld'), timeout=1.0)
                end = datetime.utcnow()
            except queue.Empty:
                pass
        self.assertEqual('Hello, World!\n', hw)
        self.assertLess(end-start, timedelta(seconds=4))
