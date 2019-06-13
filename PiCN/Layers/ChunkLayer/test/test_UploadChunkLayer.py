"""Testing the Basic Chunk Layer"""

import multiprocessing
import time
import unittest

from PiCN.Layers.ChunkLayer import RequestTableEntry
from PiCN.Layers.ChunkLayer.DataOffloadingChunkLayer import DataOffloadingChunklayer, CaEntry
from PiCN.Layers.ICNLayer.ContentStore import ContentStoreMemoryExact
from PiCN.Layers.ICNLayer.ForwardingInformationBase import ForwardingInformationBaseMemoryPrefix
from PiCN.Layers.ICNLayer.PendingInterestTable import PendingInterstTableMemoryExact
from PiCN.Packets import Content, Interest, Name, Nack, NackReason
from PiCN.Processes import PiCNSyncDataStructFactory


class test_UploadChunkLayerOptimized(unittest.TestCase):
    """Testing the Basic Chunk Layer"""

    def setUp(self):
        synced_data_struct_factory = PiCNSyncDataStructFactory()
        synced_data_struct_factory.register("cs", ContentStoreMemoryExact)
        synced_data_struct_factory.register("fib", ForwardingInformationBaseMemoryPrefix)
        synced_data_struct_factory.register("pit", PendingInterstTableMemoryExact)

        synced_data_struct_factory.create_manager()

        cs = synced_data_struct_factory.manager.cs()
        fib = synced_data_struct_factory.manager.fib()
        pit = synced_data_struct_factory.manager.pit()

        self.chunkLayer: DataOffloadingChunklayer = DataOffloadingChunklayer(cs, pit, fib)

        self.q1_to_lower = multiprocessing.Queue()
        self.q1_to_higher = multiprocessing.Queue()

        self.q1_from_lower = multiprocessing.Queue()
        self.q1_from_higher = multiprocessing.Queue()

        self.chunkLayer.queue_to_lower = self.q1_to_lower
        self.chunkLayer.queue_to_higher = self.q1_to_higher
        self.chunkLayer.queue_from_lower = self.q1_from_lower
        self.chunkLayer.queue_from_higher = self.q1_from_higher

    def tearDown(self):
        self.chunkLayer.stop_process()


    def test_name_in_chunktable(self):
        """Test if the helper to find a name in the chunktable works"""
        self.chunkLayer.start_process()

        n1 = Name("/test/data")
        n2 = Name("/data/test")
        self.chunkLayer._request_table.append(RequestTableEntry(n1))
        self.chunkLayer._request_table.append(RequestTableEntry(n2))

        result2 = self.chunkLayer.get_request_entry(n2)
        result1 = self.chunkLayer.get_request_entry(n1)

        self.assertEqual(result1.name, n1)
        self.assertEqual(result2.name, n2)

    def test_handle_received_meta_data(self):
        """test if received meta data are handled correctly"""
        self.chunkLayer.start_process()
        md1_n = Name("/test/data")
        md1 = Content(md1_n, "mdo:300:/test/data/c0;/test/data/c1;/test/data/c2;/test/data/c3:/test/data/m1")
        md2_n = Name("/test/data/m1")
        md2 = Content(md2_n, "mdo:300:/test/data/c4:")

        request_table_entry = RequestTableEntry(md1_n)

        self.chunkLayer.handle_received_meta_data(0, md1, request_table_entry, self.q1_to_lower, False, False)
        request_table_entry = self.chunkLayer.get_request_entry(md1_n)

        self.assertEqual(request_table_entry.requested_md[0], Name("/test/data/m1"))
        chunknames =  [Name("/test/data/c0"), Name("/test/data/c1"), Name("/test/data/c2"), Name("/test/data/c3"),
                       Name("/test/data/c4")]
        self.assertEqual(request_table_entry.requested_chunks, chunknames[:4])

        d1 = self.q1_to_lower.get()[1]
        self.assertEqual(d1.name, Name("/test/data/m1"))

        self.chunkLayer.handle_received_meta_data(0, md2, request_table_entry, self.q1_to_lower, True, False)

        for i in range(0,5):
            d2 = self.q1_to_lower.get()[1]
            self.assertEqual(d2.name, chunknames[i])
        self.assertTrue(self.q1_to_lower.empty())

        self.assertEqual(len(request_table_entry.requested_md), 0)
        self.assertEqual(len(request_table_entry.requested_chunks), 5)
        self.assertEqual(request_table_entry.requested_chunks, chunknames)

    def test_handle_received_chunk_data(self):
        """test if received chunk data are handled correctly"""
        self.chunkLayer.start_process()

        n1 = Name("/test/data")
        chunk1_n = Name("/test/data/c0")
        chunk2_n = Name("/test/data/c1")

        request_table_entry = RequestTableEntry(n1)
        request_table_entry.chunked = True

        self.chunkLayer._ca_table[n1] = CaEntry()

        request_table_entry.requested_chunks.append(chunk1_n)
        request_table_entry.requested_chunks.append(chunk2_n)

        chunk1 = Content(chunk1_n, "chunk1")
        chunk2 = Content(chunk2_n, "chunk2")

        self.chunkLayer.handle_received_chunk_data(0, chunk1, request_table_entry, self.q1_to_lower, self.q1_to_higher, False)
        request_table_entry = self.chunkLayer.get_request_entry(n1)
        self.assertEqual(request_table_entry.requested_chunks, [chunk2_n])

        self.chunkLayer.handle_received_chunk_data(0, chunk2, request_table_entry, self.q1_to_lower, self.q1_to_higher, False)
        request_table_entry = self.chunkLayer.get_request_entry(n1)
        self.assertEqual(len(request_table_entry.requested_md), 0)

        try:
            data = self.q1_to_higher.get(timeout=2.0)[1]
        except:
            self.fail()
        self.assertEqual(data.name, n1)
        self.assertEqual(data.content, "chunk1chunk2")


    def test_interest_from_lower_no_match(self):
        """Test handling interest from lower with no chunk entry"""
        self.chunkLayer.start_process()
        i = Interest("/test/data")
        self.chunkLayer.queue_from_lower.put([0, i])
        try:
            data = self.chunkLayer.queue_to_higher.get(timeout=2.0)
        except:
            self.fail()
        self.assertEqual(i, data[1])

    def test_interest_from_lower_match(self):
        """Test handling interest from lower with chunk entry"""
        self.chunkLayer.start_process()
        n = Name("/test/data/c0")
        i = Interest(n)
        c = Content(n, "dataobject")
        self.chunkLayer._chunk_table[c.name] = (c, time.time())
        self.chunkLayer.queue_from_lower.put([0, i])
        try:
            data = self.chunkLayer.queue_to_lower.get(timeout=2.0)
        except:
            self.fail()
        self.assertEqual(c, data[1])

    def test_interest_from_higher_no_entry(self):
        """Test handling interest from higher with no request entry"""
        self.chunkLayer.start_process()
        i = Interest("/test/data")
        self.chunkLayer.queue_from_higher.put([0, i])
        try:
            data = self.chunkLayer.queue_to_lower.get(timeout=2.0)
        except:
            self.fail()
        self.assertEqual(i, data[1])
        self.assertEqual(self.chunkLayer._request_table[0], RequestTableEntry(i.name))

    def test_interest_from_higher_entry(self):
        """Test handling interest from higher with request entry"""
        self.chunkLayer.start_process()
        i = Interest("/test/data")
        self.chunkLayer._request_table.append(RequestTableEntry(i.name))
        self.chunkLayer.queue_from_higher.put([0, i])
        time.sleep(1)
        res = self.chunkLayer.queue_to_lower.get()
        self.assertEqual(res[1], i)
        self.assertTrue(self.chunkLayer.queue_to_lower.empty())
        self.assertEqual(self.chunkLayer._request_table[0], RequestTableEntry(i.name))

    def test_content_from_higher_no_chunk(self):
        """Test handling content from higher"""
        self.chunkLayer.start_process()
        c = Content("/test/data", "content")
        self.chunkLayer.queue_from_higher.put([0, c])
        try:
            data = self.chunkLayer.queue_to_lower.get(timeout=2.0)
        except:
            self.fail()
        self.assertEqual(data[1], c)

    def test_content_from_higher_chunk(self):
        """Test handling content from higher with chunks"""
        self.chunkLayer.start_process()
        data = "A" * 4096 + "B" * 200
        c = Content("/test/data", data)
        self.chunkLayer.queue_from_higher.put([0, c])
        try:
            data = self.chunkLayer.queue_to_lower.get(timeout=2.0)
        except:
            self.fail()
        md = Content("/test/data", "mdo:4296:/test/data/c0;/test/data/c1:")
        self.assertEqual(data[1], md)

    def test_content_from_lower_no_request_table_entry(self):
        """Test handling content from lower when there is no request table entry"""
        self.chunkLayer.start_process()
        c = Content("/test/data", "content")
        self.chunkLayer.queue_from_lower.put([0, c])
        self.assertTrue(self.chunkLayer.queue_to_higher.empty())

    def test_content_from_lower_layer(self):
        """Test handling content from lower"""
        self.chunkLayer.start_process()
        n1 = Name("/test/data")
        self.chunkLayer._request_table.append(RequestTableEntry(n1))
        c1 = Content(n1, "data")
        self.chunkLayer.queue_from_lower.put([0, c1])
        try:
            data = self.chunkLayer.queue_to_higher.get()
        except:
            self.fail()
        self.assertEqual(data[1], c1)


    def test_metadata_from_lower_layer(self):
        """test receiving metadata from lower layer"""
        self.chunkLayer.start_process()
        md1_n = Name("/test/data")
        md1 = Content(md1_n, "mdo:300:/test/data/c0;/test/data/c1;/test/data/c2;/test/data/c3:/test/data/m1")
        md2_n = Name("/test/data/m1")
        md2 = Content(md2_n, "mdo:300:/test/data/c4:")

        chunknames = [Name("/test/data/c0"), Name("/test/data/c1"), Name("/test/data/c2"), Name("/test/data/c3"),
                      Name("/test/data/c4")]

        self.chunkLayer._request_table.append(RequestTableEntry(md1_n))
        ca_entry = CaEntry()
        ca_entry.received_all = True
        self.chunkLayer._ca_table[md1_n] = ca_entry

        self.chunkLayer.queue_from_lower.put([0, md1])

        data = self.chunkLayer.queue_to_lower.get()
        self.assertEqual(Interest(md2_n), data[1])

        self.chunkLayer.queue_from_lower.put([0, md2])
        request: RequestTableEntry = self.chunkLayer.get_request_entry(md1_n)
        self.assertEqual(request.requested_chunks, chunknames[:4])
        self.assertEqual(request.requested_md[0], md2_n)

        for i in range(0,5):
            data = self.chunkLayer.queue_to_lower.get()[1]
            self.assertEqual(Interest(chunknames[i]), data)

        self.assertTrue(self.chunkLayer.queue_to_lower.empty())

        time.sleep(1)

        request: RequestTableEntry = self.chunkLayer.get_request_entry(md1_n)

        self.assertEqual(len(request.requested_md), 0)
        self.assertEqual(len(request.requested_chunks), 5)
        self.assertEqual(request.requested_chunks, chunknames)

    def test_chunk_from_lower_layer(self):
        """test receiving metadata from lower layer"""
        self.chunkLayer.start_process()

        n1 = Name("/test/data")
        re1 = RequestTableEntry(n1)
        re1.chunked = True

        chunk1_n = Name("/test/data/c0")
        chunk2_n = Name("/test/data/c1")

        chunk1 = Content(chunk1_n, "chunk1")
        chunk2 = Content(chunk2_n, "chunk2")

        re1.requested_chunks.append(chunk1_n)
        re1.requested_chunks.append(chunk2_n)

        self.chunkLayer._request_table.append(re1)
        self.chunkLayer._ca_table[n1] = CaEntry()

        self.chunkLayer.queue_from_lower.put([0, chunk2])
        time.sleep(1)
        self.assertTrue(self.chunkLayer.queue_to_higher.empty())

        self.chunkLayer.queue_from_lower.put([0, chunk1])

        try:
            data = self.chunkLayer.queue_to_higher.get(timeout=2.0)
        except:
            self.fail()

        self.assertEqual(data[1].content, "chunk1chunk2")

    def test_nack_from_higher(self):
        """Test nack from higher"""
        self.chunkLayer.start_process()
        interest = Interest("/test/data")
        nack1 = Nack("/test/data", NackReason.NO_CONTENT, interest=interest)
        self.chunkLayer.queue_from_higher.put([1, nack1])
        try:
            data = self.chunkLayer.queue_to_lower.get(timeout=2.0)
        except:
            self.fail()
        self.assertEqual(data[0], 1)
        self.assertEqual(data[1], nack1)

    def test_nack_from_lower(self):
        """Test nack from lower"""
        self.chunkLayer.start_process()
        nack1 = Nack("/test/data", NackReason.NO_CONTENT, None)
        self.chunkLayer.queue_from_lower.put([1, nack1])
        try:
            data = self.chunkLayer.queue_to_higher.get(timeout=2.0)
        except:
            self.fail()
        self.assertEqual(data[0], 1)
        self.assertEqual(data[1], nack1)

    def test_ca_interest_sent(self):
        """Test if ca message is generated and sent"""
        self.chunkLayer.start_process()
        interest = Interest("/car/test/data")
        cl_interest_name = Name("/nL/car/test/data/CA1")

        self.chunkLayer.fib.add_fib_entry(Name("/nL"), [1])
        self.chunkLayer.queue_from_higher.put([0, interest])

        try:
            data = self.chunkLayer.queue_to_lower.get(timeout=2.0)[1]
        except:
            self.fail()

        self.assertEqual(data.name, cl_interest_name)

