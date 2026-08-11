"""Async tests for AsyncBasicNFNLayer (Task 4.6).

Plain pytest module -- see ADR-010's Addendum.
"""

import asyncio
import multiprocessing
from concurrent.futures import ThreadPoolExecutor

import pytest

from PiCN.Layers.ICNLayer.ContentStore import ContentStoreMemoryExact
from PiCN.Layers.ICNLayer.ForwardingInformationBase import ForwardingInformationBaseMemoryPrefix
from PiCN.Layers.ICNLayer.PendingInterestTable import PendingInterstTableMemoryExact
from PiCN.Layers.LinkLayer.FaceIDTable import FaceIDDict
from PiCN.Layers.NFNLayer.AsyncBasicNFNLayer import AsyncBasicNFNLayer
from PiCN.Layers.NFNLayer.NFNComputationTable import NFNComputationList, NFNComputationTableEntry
from PiCN.Layers.NFNLayer.NFNExecutor import NFNPythonExecutor
from PiCN.Layers.NFNLayer.Parser import DefaultNFNParser
from PiCN.Layers.NFNLayer.R2C import TimeoutR2CHandler
from PiCN.Packets import Content, Interest, Name
from PiCN.Processes import PiCNSyncDataStructFactory


class TestAsyncBasicNFNLayer:
    def setup_method(self):
        synced_data_struct_factory = PiCNSyncDataStructFactory()
        synced_data_struct_factory.register("cs", ContentStoreMemoryExact)
        synced_data_struct_factory.register("fib", ForwardingInformationBaseMemoryPrefix)
        synced_data_struct_factory.register("pit", PendingInterstTableMemoryExact)
        synced_data_struct_factory.register("computation_table", NFNComputationList)
        synced_data_struct_factory.register("faceidtable", FaceIDDict)
        synced_data_struct_factory.create_manager()

        cs = synced_data_struct_factory.manager.cs()
        fib = synced_data_struct_factory.manager.fib()
        pit = synced_data_struct_factory.manager.pit()
        faceidtable = synced_data_struct_factory.manager.faceidtable()

        r2cclient = TimeoutR2CHandler()
        parser = DefaultNFNParser()
        comp_table = synced_data_struct_factory.manager.computation_table(r2cclient, parser)
        nfn_executors = {"PYTHON": NFNPythonExecutor()}

        self._thread_pool = ThreadPoolExecutor(max_workers=2)
        self.layer = AsyncBasicNFNLayer(
            cs,
            fib,
            pit,
            faceidtable,
            comp_table,
            nfn_executors,
            parser,
            r2cclient,
            log_level=255,
            executor=self._thread_pool,
        )
        self.to_lower: asyncio.Queue = asyncio.Queue(maxsize=16)
        self.to_higher: asyncio.Queue = asyncio.Queue(maxsize=16)
        self.layer.queue_to_lower = self.to_lower

    def teardown_method(self):
        self._thread_pool.shutdown(wait=True)

    @pytest.mark.asyncio
    async def test_compute_no_params_via_executor(self):
        computation_name = Name("/func/f1")
        computation_name += "_()"
        computation_name += "NFN"
        computation_interest = Interest(computation_name)

        computation_entry = NFNComputationTableEntry(computation_name)
        computation_entry.available_data[Name("/func/f1")] = "PYTHON\nf\ndef f():\n    return 25"

        computation_str, _ = self.layer.parser.network_name_to_nfn_str(computation_name)
        computation_entry.ast = self.layer.parser.parse(computation_str)
        self.layer.computation_table.append_computation(computation_entry)

        await self.layer.compute(computation_interest)

        face_id, packet = self.to_lower.get_nowait()
        assert face_id == computation_entry.id
        assert packet == Content(computation_name, "25")
        assert self.to_lower.empty()
