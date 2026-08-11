"""Shared runtime selection helpers for ProgramLibs (Phase 5).

``Runtime.SYNC`` (default) keeps today's multiprocessing Manager tables.
``Runtime.ASYNC`` constructs plain in-process CS/FIB/PIT/FaceIDTable (and
optional RIB) objects -- no ``PiCNSyncDataStructFactory`` / Manager.
"""

from enum import Enum
from typing import NamedTuple, Optional, Union

from PiCN.Layers.ICNLayer.ContentStore import ContentStoreMemoryExact
from PiCN.Layers.ICNLayer.ForwardingInformationBase import (
    ForwardingInformationBaseMemoryPrefix,
)
from PiCN.Layers.ICNLayer.PendingInterestTable import PendingInterstTableMemoryExact
from PiCN.Layers.LinkLayer.FaceIDTable import FaceIDDict
from PiCN.Layers.RoutingLayer.RoutingInformationBase import TreeRoutingInformationBase
from PiCN.Processes import PiCNSyncDataStructFactory


class Runtime(str, Enum):
    """How a ProgramLib builds its layer stack and data structures."""

    SYNC = "sync"
    ASYNC = "async"


class ForwardingTables(NamedTuple):
    """Core forwarding tables shared by ICN/NFN node builders."""

    cs: ContentStoreMemoryExact
    fib: ForwardingInformationBaseMemoryPrefix
    pit: PendingInterstTableMemoryExact
    faceidtable: FaceIDDict
    rib: Optional[TreeRoutingInformationBase]


def make_forwarding_tables(
    runtime: Union[Runtime, str] = Runtime.SYNC,
    *,
    routing: bool = False,
) -> ForwardingTables:
    """Create CS, FIB, PIT, FaceIDTable, and optionally RIB.

    :param runtime: ``Runtime.SYNC`` uses a Manager-backed factory;
        ``Runtime.ASYNC`` constructs plain in-process objects.
    :param routing: if True, also create a TreeRoutingInformationBase.
    :return: ForwardingTables named tuple.
    """
    if isinstance(runtime, str):
        runtime = Runtime(runtime)

    if runtime is Runtime.ASYNC:
        cs = ContentStoreMemoryExact()
        fib = ForwardingInformationBaseMemoryPrefix()
        pit = PendingInterstTableMemoryExact()
        faceidtable = FaceIDDict()
        rib = TreeRoutingInformationBase() if routing else None
        return ForwardingTables(cs, fib, pit, faceidtable, rib)

    factory = PiCNSyncDataStructFactory()
    factory.register("cs", ContentStoreMemoryExact)
    factory.register("fib", ForwardingInformationBaseMemoryPrefix)
    factory.register("pit", PendingInterstTableMemoryExact)
    factory.register("faceidtable", FaceIDDict)
    if routing:
        factory.register("rib", TreeRoutingInformationBase)
    factory.create_manager()

    cs = factory.manager.cs()
    fib = factory.manager.fib()
    pit = factory.manager.pit()
    faceidtable = factory.manager.faceidtable()
    rib = factory.manager.rib() if routing else None
    return ForwardingTables(cs, fib, pit, faceidtable, rib)
