"""
Repo that move along edge nodes given the following structure. Node: Test requires some computational power and takes
some time! If it fails maybe more computational power is required!
                       c00
             _________/ | \_________
            |           |           |
            |           |           |
           c10         c20         c30
         /  |  \      / |  \      / | \
       e11 e12 e13 e21 e22 e23 e31 e32 e33

       """


from typing import List, Tuple, Dict

import multiprocessing
import os
import shutil
import queue
from datetime import timedelta
from time import sleep

from PiCN.Layers.ICNLayer.ForwardingInformationBase import BaseForwardingInformationBase
from PiCN.Layers.LinkLayer.Interfaces import AddressInfo
from PiCN.Layers.PacketEncodingLayer.Encoder import NdnTlvEncoder
from PiCN.Packets import Name
from PiCN.ProgramLibs.Fetch import Fetch
from PiCN.ProgramLibs.ICNDataRepository import ICNDataRepository
from PiCN.ProgramLibs.ICNForwarder import ICNForwarder


class AutoconfigRepoHoppingSimulation(object):

    def setUp(self):
        """
                        c00
              _________/ | \_________
             |           |           |
             |           |           |
            c10         c20         c30
          /  |  \      / |  \      / | \
        e11 e12 e13 e21 e22 e23 e31 e32 e33

        """

        self.manager = multiprocessing.Manager()
        self.autoconfig_edgeprefix: List[Tuple[Name, bool]] = [(Name('/edge'), False)]
        self.nodes: Dict[int, ICNForwarder] = dict()
        self.ports: Dict[int, int] = dict()

        # Initialize core nodes
        for c in [00, 10, 20, 30]:
            self.nodes[c] = ICNForwarder(0, encoder=NdnTlvEncoder(), routing=True, peers=[])
            self.ports[c] = self.nodes[c].linklayer.interfaces[0].get_port()
        # Initialize edge nodes
        for e in [11, 12, 13, 21, 22, 23, 31, 32, 33]:
            self.nodes[e] = ICNForwarder(0, encoder=NdnTlvEncoder(), routing=True, peers=[], autoconfig=True)
            self.ports[e] = self.nodes[e].linklayer.interfaces[0].get_port()

        # Assign routing peers after the OS assigned UDP ports. Each node knows the nodes one layer "beneath" itself
        # in above graph as its routing peers.
        self.nodes[00].routinglayer._peers = [('127.0.0.1', self.ports[10]),
                                              ('127.0.0.1', self.ports[20]),
                                              ('127.0.0.1', self.ports[30])]
        self.nodes[10].routinglayer._peers = [('127.0.0.1', self.ports[11]),
                                              ('127.0.0.1', self.ports[12]),
                                              ('127.0.0.1', self.ports[13])]
        self.nodes[20].routinglayer._peers = [('127.0.0.1', self.ports[21]),
                                              ('127.0.0.1', self.ports[22]),
                                              ('127.0.0.1', self.ports[23])]
        self.nodes[30].routinglayer._peers = [('127.0.0.1', self.ports[31]),
                                              ('127.0.0.1', self.ports[32]),
                                              ('127.0.0.1', self.ports[33])]

        # Set up faces and static FIB of core00 node.
        fid00to10: int = self.nodes[00].linklayer.faceidtable.get_or_create_faceid(AddressInfo(('127.0.0.1', self.ports[10]), 0))
        fid00to20: int = self.nodes[00].linklayer.faceidtable.get_or_create_faceid(AddressInfo(('127.0.0.1', self.ports[20]), 0))
        fid00to30: int = self.nodes[00].linklayer.faceidtable.get_or_create_faceid(AddressInfo(('127.0.0.1', self.ports[30]), 0))
        fib00: BaseForwardingInformationBase = self.nodes[00].icnlayer.fib
        fib00.add_fib_entry(Name('/edge'), [fid00to10], static=True)
        fib00.add_fib_entry(Name('/edge'), [fid00to20], static=True)
        fib00.add_fib_entry(Name('/edge'), [fid00to30], static=True)
        self.nodes[00].routinglayer.rib.shortest_only = False

        # Set up faces and static FIB of core10 node.
        fid10to11: int = self.nodes[10].linklayer.faceidtable.get_or_create_faceid(AddressInfo(('127.0.0.1', self.ports[11]), 0))
        fid10to12: int = self.nodes[10].linklayer.faceidtable.get_or_create_faceid(AddressInfo(('127.0.0.1', self.ports[12]), 0))
        fid10to13: int = self.nodes[10].linklayer.faceidtable.get_or_create_faceid(AddressInfo(('127.0.0.1', self.ports[13]), 0))
        fib10: BaseForwardingInformationBase = self.nodes[10].icnlayer.fib
        fib10.add_fib_entry(Name('/edge'), [fid10to11], static=True)
        fib10.add_fib_entry(Name('/edge'), [fid10to12], static=True)
        fib10.add_fib_entry(Name('/edge'), [fid10to13], static=True)
        self.nodes[10].routinglayer.rib.shortest_only = False

        # Set up faces and static FIB of core20 node.
        fid20to21: int = self.nodes[20].linklayer.faceidtable.get_or_create_faceid(AddressInfo(('127.0.0.1', self.ports[21]), 0))
        fid20to22: int = self.nodes[20].linklayer.faceidtable.get_or_create_faceid(AddressInfo(('127.0.0.1', self.ports[22]), 0))
        fid20to23: int = self.nodes[20].linklayer.faceidtable.get_or_create_faceid(AddressInfo(('127.0.0.1', self.ports[23]), 0))
        fib20: BaseForwardingInformationBase = self.nodes[20].icnlayer.fib
        fib20.add_fib_entry(Name('/edge'), [fid20to21], static=True)
        fib20.add_fib_entry(Name('/edge'), [fid20to22], static=True)
        fib20.add_fib_entry(Name('/edge'), [fid20to23], static=True)
        self.nodes[20].routinglayer.rib.shortest_only = False

        # Set up faces and static FIB of core30 node.
        fid30to31: int = self.nodes[30].linklayer.faceidtable.get_or_create_faceid(AddressInfo(('127.0.0.1', self.ports[31]), 0))
        fid30to32: int = self.nodes[30].linklayer.faceidtable.get_or_create_faceid(AddressInfo(('127.0.0.1', self.ports[32]), 0))
        fid30to33: int = self.nodes[30].linklayer.faceidtable.get_or_create_faceid(AddressInfo(('127.0.0.1', self.ports[33]), 0))
        fib30: BaseForwardingInformationBase = self.nodes[30].icnlayer.fib
        fib30.add_fib_entry(Name('/edge'), [fid30to31], static=True)
        fib30.add_fib_entry(Name('/edge'), [fid30to32], static=True)
        fib30.add_fib_entry(Name('/edge'), [fid30to33], static=True)
        self.nodes[30].routinglayer.rib.shortest_only = False

        self.nodes[00].routinglayer._ageing_interval = 1.0
        self.nodes[10].routinglayer._ageing_interval = 1.0
        self.nodes[20].routinglayer._ageing_interval = 1.0
        self.nodes[30].routinglayer._ageing_interval = 1.0

        # Set up network edge autoconfig.
        for e in [11, 12, 13, 21, 22, 23, 31, 32, 33]:
            self.nodes[e].autoconfiglayer._service_registration_prefixes = self.autoconfig_edgeprefix
            self.nodes[e].routinglayer._ageing_interval = 1.0
            self.nodes[e].autoconfiglayer._service_registration_timeout = timedelta(seconds=15)
        # Set up repository directory.
        os.makedirs('/tmp/test_hopping_repo', exist_ok=True)
        for c in [1, 2, 3, 4, 5, 6, 7, 8, 9]:
            with open(f'/tmp/test_hopping_repo/c{c}', 'w') as f:
                f.write(f'This is test chunk {c}!')

    def tearDown(self):
        for n in self.nodes.values():
            n.stop_forwarder()
        shutil.rmtree('/tmp/test_hopping_repo')

    def run_simulation(self):
        for n in self.nodes.values():
            n.start_forwarder()

        chunks: List[str] = []
        for i, edge in [(1, 11), (2, 12), (3, 13), (4, 21), (5, 22), (6, 23), (7, 31), (8, 32), (9, 33)]:
            # Instead of moving a single repo from one node to the next, it's far easier to simply create a new one, and
            # it SHOULDN'T make a difference.
            repo = ICNDataRepository('/tmp/test_hopping_repo', Name('/hoppingrepo'), 0, encoder=NdnTlvEncoder(),
                                     autoconfig=True, autoconfig_routed=True)
            repo.autoconfiglayer._broadcast_port = self.ports[edge]
            repo.start_repo()
            sleep(10)
            # Start a fetch client which sends its interests to the core00 node
            fetch = Fetch('127.0.0.1', self.ports[00], encoder=NdnTlvEncoder())
            for _ in range(5):
                try:
                    chunks.append(fetch.fetch_data(Name(f'/edge/hoppingrepo/c{i}'), timeout=4.0))
                    break
                except queue.Empty:
                    pass
            fetch.stop_fetch()
            repo.stop_repo()
        expected: List[str] = []
        for c in [1, 2, 3, 4, 5, 6, 7, 8, 9]:
            expected.append(f'This is test chunk {c}!')
        if expected == chunks:
            print("Test was successful executed")
        else:
            print("Error during test")

if __name__ == "__main__":
    test = AutoconfigRepoHoppingSimulation()
    try:
        test.setUp()
        test.run_simulation()
    finally:
        test.tearDown()
