
import unittest
import multiprocessing
import time
import queue

from PiCN.LayerStack import LayerStack
from PiCN.Layers.ICNLayer import BasicICNLayer
from PiCN.Layers.LinkLayer.FaceIDTable import FaceIDDict
from PiCN.Layers.LinkLayer.Interfaces import UDP4Interface
from PiCN.Layers.PacketEncodingLayer import BasicPacketEncodingLayer
from PiCN.Layers.PacketEncodingLayer.Encoder import NdnTlvEncoder
from PiCN.Layers.LinkLayer import BasicLinkLayer
from PiCN.Layers.RepositoryLayer import BasicRepositoryLayer
from PiCN.Layers.AutoconfigLayer import AutoconfigServerLayer, AutoconfigClientLayer, AutoconfigRepoLayer
from PiCN.Layers.ICNLayer.ContentStore import ContentStoreMemoryExact
from PiCN.Layers.ICNLayer.PendingInterestTable import PendingInterstTableMemoryExact
from PiCN.Layers.ICNLayer.ForwardingInformationBase import ForwardingInformationBaseMemoryPrefix
from PiCN.Layers.ChunkLayer import BasicChunkLayer
from PiCN.Layers.ChunkLayer.Chunkifyer import SimpleContentChunkifyer

from PiCN.Packets import Name, Interest, Content

from PiCN.Layers.AutoconfigLayer.test.mocks import MockRepository
from PiCN.Processes import PiCNSyncDataStructFactory


class test_AutoconfigFullStack(unittest.TestCase):

    def setUp(self):
        synced_data_struct_factory = PiCNSyncDataStructFactory()
        synced_data_struct_factory.register('cs', ContentStoreMemoryExact)
        synced_data_struct_factory.register('pit', PendingInterstTableMemoryExact)
        synced_data_struct_factory.register('fib', ForwardingInformationBaseMemoryPrefix)
        synced_data_struct_factory.register('faceidtable', FaceIDDict)
        synced_data_struct_factory.create_manager()
        # Set up forwarder
        cs = synced_data_struct_factory.manager.cs()
        pit = synced_data_struct_factory.manager.pit()
        fib = synced_data_struct_factory.manager.fib()
        prefixes = [(Name('/test/prefix/repos'), True)]
        # Auto-assign port
        forwarder_interface = UDP4Interface(0)
        forwarder_fidtable = synced_data_struct_factory.manager.faceidtable()
        forwarder_linklayer = BasicLinkLayer([forwarder_interface], forwarder_fidtable)
        forwarder_port = forwarder_interface.get_port()
        forwarder_encoder = NdnTlvEncoder()
        icnlayer = BasicICNLayer()
        icnlayer.cs = cs
        icnlayer.pit = pit
        icnlayer.fib = fib
        forwarder_autoconfiglayer = AutoconfigServerLayer(forwarder_linklayer,
                                                          registration_prefixes=prefixes)
        forwarder_autoconfiglayer.fib = fib
        self.forwarder = LayerStack([
            icnlayer,
            forwarder_autoconfiglayer,
            BasicPacketEncodingLayer(forwarder_encoder),
            forwarder_linklayer
        ])

        # Set up repo
        repository = MockRepository(Name('/thisshouldbechanged'))
        repo_chunkifyer = SimpleContentChunkifyer()
        repo_chunklayer = BasicChunkLayer(repo_chunkifyer)
        repo_encoder = NdnTlvEncoder()
        # Auto-assign port
        repo_interface = UDP4Interface(0)
        repo_fidtable = synced_data_struct_factory.manager.faceidtable()
        repo_linklayer = BasicLinkLayer([repo_interface], repo_fidtable)
        repo_port = repo_interface.get_port()
        self.repo = LayerStack([
            BasicRepositoryLayer(repository),
            repo_chunklayer,
            AutoconfigRepoLayer('testrepo', repo_linklayer, repository, '127.0.0.1', forwarder_port),
            BasicPacketEncodingLayer(repo_encoder),
            repo_linklayer
        ])

        # Set up fetch client
        client_chunkifyer = SimpleContentChunkifyer()
        client_chunklayer = BasicChunkLayer(client_chunkifyer)
        client_encoder = NdnTlvEncoder()
        client_interface = UDP4Interface(0)
        client_fidtable = synced_data_struct_factory.manager.faceidtable()
        client_linklayer = BasicLinkLayer([client_interface], client_fidtable)
        self.client = LayerStack([
            client_chunklayer,
            AutoconfigClientLayer(client_linklayer, bcport=forwarder_port),
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
        try:
            data = self.client.queue_to_higher.get(timeout=20.0)
        except queue.Empty:
            self.fail()
        self.assertIsInstance(data[1], Content)
        self.assertEqual(data[1].name, name)
        self.assertEqual(data[1].content, 'testcontent')
