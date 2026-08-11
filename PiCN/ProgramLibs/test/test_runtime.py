"""Tests for ProgramLibs.runtime helpers (Task 5.0)."""

from PiCN.Layers.ICNLayer.ContentStore import ContentStoreMemoryExact
from PiCN.Layers.LinkLayer.FaceIDTable import FaceIDDict
from PiCN.ProgramLibs.runtime import Runtime, make_forwarding_tables


class TestMakeForwardingTables:
    def test_async_returns_plain_in_process_objects(self):
        tables = make_forwarding_tables(Runtime.ASYNC)
        assert isinstance(tables.cs, ContentStoreMemoryExact)
        assert isinstance(tables.faceidtable, FaceIDDict)
        assert tables.rib is None
        # Plain objects: no Manager proxy (no _manager / _id attributes).
        assert not hasattr(tables.cs, "_manager")

    def test_async_with_routing_includes_rib(self):
        tables = make_forwarding_tables(Runtime.ASYNC, routing=True)
        assert tables.rib is not None

    def test_sync_returns_manager_backed_tables(self):
        tables = make_forwarding_tables(Runtime.SYNC)
        assert tables.cs is not None
        assert tables.fib is not None
        assert tables.pit is not None
        assert tables.faceidtable is not None
        assert tables.rib is None

    def test_string_runtime_accepted(self):
        tables = make_forwarding_tables("async")
        assert isinstance(tables.faceidtable, FaceIDDict)
