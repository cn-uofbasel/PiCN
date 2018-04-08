
import unittest
import multiprocessing
import time

from PiCN.LayerStack import LayerStack
from PiCN.Layers.ICNLayer import BasicICNLayer
from PiCN.Layers.PacketEncodingLayer import BasicPacketEncodingLayer
from PiCN.Layers.PacketEncodingLayer.Encoder import NdnTlvEncoder
from PiCN.Layers.LinkLayer import UDP4LinkLayer
from PiCN.Layers.RepositoryLayer import BasicRepositoryLayer
from PiCN.Layers.AutoconfigLayer import AutoconfigServerLayer, AutoconfigClientLayer, AutoconfigRepoLayer
from PiCN.Layers.ICNLayer.ContentStore import ContentStoreMemoryExact
from PiCN.Layers.ICNLayer.PendingInterestTable import PendingInterstTableMemoryExact
from PiCN.Layers.ICNLayer.ForwardingInformationBase import ForwardingInformationBaseMemoryPrefix
from PiCN.Layers.ChunkLayer import BasicChunkLayer
from PiCN.Layers.ChunkLayer.Chunkifyer import SimpleContentChunkifyer

from PiCN.Packets import Name, Interest, Content

from PiCN.Layers.AutoconfigLayer.test.mocks import MockRepository


class test_AutoconfigFullStack(unittest.TestCase):

    def setUp(self):

        # Set up forwarder
        manager = multiprocessing.Manager()
        cs = ContentStoreMemoryExact(manager)
        pit = PendingInterstTableMemoryExact(manager)
        fib = ForwardingInformationBaseMemoryPrefix(manager)
        prefixes = [Name('/test/prefix/repos')]
        forwarder_linklayer = UDP4LinkLayer(port=9000, manager=manager)
        forwarder_encoder = NdnTlvEncoder()
        self.forwarder = LayerStack([
            BasicICNLayer(cs, pit, fib),
            AutoconfigServerLayer(forwarder_linklayer, fib,
                                  registration_prefixes=prefixes, broadcast='127.255.255.255'),
            BasicPacketEncodingLayer(forwarder_encoder),
            forwarder_linklayer
        ])

        # Set up repo
        repository = MockRepository(Name('/thisshouldbechanged'))
        repo_chunkifyer = SimpleContentChunkifyer()
        repo_chunklayer = BasicChunkLayer(repo_chunkifyer)
        repo_encoder = NdnTlvEncoder()
        repo_linklayer = UDP4LinkLayer(port=9001, manager=manager)
        self.repo = LayerStack([
            BasicRepositoryLayer(repository),
            repo_chunklayer,
            AutoconfigRepoLayer('testrepo', repo_linklayer, repository, '127.0.0.1', 9001, bcaddr='127.255.255.255'),
            BasicPacketEncodingLayer(repo_encoder),
            repo_linklayer
        ])

        # Set up fetch client
        client_chunkifyer = SimpleContentChunkifyer()
        client_chunklayer = BasicChunkLayer(client_chunkifyer)
        client_encoder = NdnTlvEncoder()
        client_linklayer = UDP4LinkLayer(port=9002, manager=manager)
        self.client = LayerStack([
            client_chunklayer,
            AutoconfigClientLayer(client_linklayer, broadcast='127.255.255.255'),
            BasicPacketEncodingLayer(client_encoder),
            client_linklayer
        ])

    def tearDown(self):
        self.forwarder.stop_all()
        self.repo.stop_all()
        self.client.stop_all()

    def test_repo_forwarder_client_fetch_fixed_name(self):
        self.forwarder.start_all()
        time.sleep(2.0)
        self.repo.start_all()
        time.sleep(2.0)
        self.client.start_all()
        time.sleep(2.0)

        # Send an interest with a fixed name, let autoconfig figure out where to get the data from
        name = Name('/test/prefix/repos/testrepo/testcontent')
        interest = Interest(name)
        self.client.queue_from_higher.put([None, interest])
        data = self.client.queue_to_higher.get(timeout=10.0)
        self.assertIsInstance(data[1], Content)
        self.assertEqual(data[1].name, name)
        self.assertEqual(data[1].content, 'testcontent')
