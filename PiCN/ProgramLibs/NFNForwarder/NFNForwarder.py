"""NFN Forwarder for PICN"""

from typing import List, Union

from PiCN.LayerStack import LayerStack
from PiCN.LayerStack.AsyncLayerStack import AsyncLayerStack
from PiCN.Layers.NFNLayer import BasicNFNLayer
from PiCN.Layers.NFNLayer.AsyncBasicNFNLayer import AsyncBasicNFNLayer
from PiCN.Layers.ChunkLayer import BasicChunkLayer, AsyncBasicChunkLayer
from PiCN.Layers.ICNLayer import BasicICNLayer, AsyncBasicICNLayer
from PiCN.Layers.PacketEncodingLayer import (
    BasicPacketEncodingLayer,
    AsyncBasicPacketEncodingLayer,
)
from PiCN.Layers.LinkLayer import BasicLinkLayer, AsyncBasicLinkLayer

from PiCN.Layers.ChunkLayer.Chunkifyer import SimpleContentChunkifyer
from PiCN.Layers.ICNLayer.ForwardingInformationBase import (
    ForwardingInformationBaseMemoryPrefix,
)
from PiCN.Layers.ICNLayer.PendingInterestTable import PendingInterstTableMemoryExact
from PiCN.Layers.NFNLayer.R2C import TimeoutR2CHandler
from PiCN.Layers.NFNLayer.NFNExecutor import NFNPythonExecutor, BaseNFNExecutor
from PiCN.Layers.NFNLayer.NFNComputationTable import NFNComputationList
from PiCN.Layers.TimeoutPreventionLayer import (
    BasicTimeoutPreventionLayer,
    AsyncBasicTimeoutPreventionLayer,
    TimeoutPreventionMessageDict,
)
from PiCN.Layers.ICNLayer.ContentStore import ContentStoreMemoryExact
from PiCN.Layers.PacketEncodingLayer.Encoder import BasicEncoder, SimpleStringEncoder
from PiCN.Layers.NFNLayer.Parser import DefaultNFNParser
from PiCN.Layers.ThunkLayer import BasicThunkLayer
from PiCN.Layers.ThunkLayer.AsyncBasicThunkLayer import AsyncBasicThunkLayer
from PiCN.Logger import Logger
from PiCN.Mgmt import Mgmt, AsyncMgmt
from PiCN.Processes import PiCNSyncDataStructFactory
from PiCN.Layers.LinkLayer.Interfaces import UDP4Interface, BaseInterface
from PiCN.Layers.LinkLayer.FaceIDTable import FaceIDDict
from PiCN.Layers.ThunkLayer.PlanTable import PlanTable
from PiCN.Layers.ThunkLayer.ThunkTable import ThunkList
from PiCN.Layers.NFNLayer.NFNOptimizer import ThunkPlanExecutor
from PiCN.ProgramLibs.runtime import Runtime


class NFNForwarder(object):
    """NFN Forwarder for PICN

    :param runtime: ``Runtime.SYNC`` (default) or ``Runtime.ASYNC``.
    """

    def __init__(
        self,
        port=9000,
        log_level=255,
        encoder: BasicEncoder = None,
        interfaces: List[BaseInterface] = None,
        executors: BaseNFNExecutor = None,
        ageing_interval: int = 3,
        use_thunks=False,
        runtime: Union[Runtime, str] = Runtime.SYNC,
    ):
        if isinstance(runtime, str):
            runtime = Runtime(runtime)
        self.runtime = runtime

        logger = Logger("NFNForwarder", log_level)
        logger.info("Start PiCN NFN Forwarder on port " + str(port))

        if encoder is None:
            self.encoder = SimpleStringEncoder(log_level=log_level)
        else:
            encoder.set_log_level(log_level)
            self.encoder = encoder

        self.parser = DefaultNFNParser()
        self.chunkifier = SimpleContentChunkifyer()
        self.r2cclient = TimeoutR2CHandler()
        if executors is None:
            self.executors = {"PYTHON": NFNPythonExecutor()}
        else:
            self.executors = executors

        if runtime is Runtime.ASYNC:
            cs = ContentStoreMemoryExact()
            fib = ForwardingInformationBaseMemoryPrefix()
            pit = PendingInterstTableMemoryExact()
            faceidtable = FaceIDDict()
            comp_table = NFNComputationList(self.r2cclient, self.parser)
            timeoutprevention_dict = TimeoutPreventionMessageDict()
            thunktable = ThunkList() if use_thunks else None
            plantable = PlanTable(self.parser) if use_thunks else None
        else:
            synced_data_struct_factory = PiCNSyncDataStructFactory()
            synced_data_struct_factory.register("cs", ContentStoreMemoryExact)
            synced_data_struct_factory.register(
                "fib", ForwardingInformationBaseMemoryPrefix)
            synced_data_struct_factory.register(
                "pit", PendingInterstTableMemoryExact)
            synced_data_struct_factory.register("faceidtable", FaceIDDict)
            synced_data_struct_factory.register(
                "computation_table", NFNComputationList)
            synced_data_struct_factory.register(
                "timeoutprevention_dict", TimeoutPreventionMessageDict)
            if use_thunks:
                synced_data_struct_factory.register("thunktable", ThunkList)
                synced_data_struct_factory.register("plantable", PlanTable)
            synced_data_struct_factory.create_manager()

            cs = synced_data_struct_factory.manager.cs()
            fib = synced_data_struct_factory.manager.fib()
            pit = synced_data_struct_factory.manager.pit()
            faceidtable = synced_data_struct_factory.manager.faceidtable()
            comp_table = synced_data_struct_factory.manager.computation_table(
                self.r2cclient, self.parser)
            timeoutprevention_dict = (
                synced_data_struct_factory.manager.timeoutprevention_dict())
            if use_thunks:
                thunktable = synced_data_struct_factory.manager.thunktable()
                plantable = synced_data_struct_factory.manager.plantable(
                    self.parser)

        if interfaces is not None:
            self.interfaces = interfaces
            mgmt_port = port
        else:
            interfaces = [UDP4Interface(port)]
            self.interfaces = interfaces
            mgmt_port = interfaces[0].get_port()

        if runtime is Runtime.ASYNC:
            self.linklayer = AsyncBasicLinkLayer(
                interfaces, faceidtable, log_level=log_level)
            self.packetencodinglayer = AsyncBasicPacketEncodingLayer(
                self.encoder, log_level=log_level)
            self.icnlayer = AsyncBasicICNLayer(
                log_level=log_level, ageing_interval=ageing_interval)
            self.chunklayer = AsyncBasicChunkLayer(
                self.chunkifier, log_level=log_level)
            self.icnlayer._interest_to_app = True
            self.nfnlayer = AsyncBasicNFNLayer(
                cs, fib, pit, faceidtable, comp_table, self.executors,
                self.parser, self.r2cclient, log_level=log_level)
            if use_thunks:
                self.thunk_layer = AsyncBasicThunkLayer(
                    cs, fib, pit, faceidtable, thunktable, plantable,
                    self.parser, log_level=log_level)
                self.nfnlayer.optimizer = ThunkPlanExecutor(
                    cs, fib, pit, faceidtable, plantable)
            self.timeoutpreventionlayer = AsyncBasicTimeoutPreventionLayer(
                timeoutprevention_dict, comp_table, pit=pit, log_level=log_level)
            layers = [
                self.nfnlayer,
                self.chunklayer,
                self.timeoutpreventionlayer,
            ]
            if use_thunks:
                layers.append(self.thunk_layer)
            layers.extend([
                self.icnlayer,
                self.packetencodinglayer,
                self.linklayer,
            ])
            self.lstack = AsyncLayerStack(layers)
            self.mgmt = AsyncMgmt(
                cs, fib, pit, self.linklayer, mgmt_port,
                self.stop_forwarder_async, log_level=log_level)
        else:
            self.linklayer = BasicLinkLayer(
                interfaces, faceidtable, log_level=log_level)
            self.packetencodinglayer = BasicPacketEncodingLayer(
                self.encoder, log_level=log_level)
            self.icnlayer = BasicICNLayer(
                log_level=log_level, ageing_interval=ageing_interval)
            self.chunklayer = BasicChunkLayer(
                self.chunkifier, log_level=log_level)
            self.icnlayer._interest_to_app = True
            self.nfnlayer = BasicNFNLayer(
                cs, fib, pit, faceidtable, comp_table, self.executors,
                self.parser, self.r2cclient, log_level=log_level)
            if use_thunks:
                self.thunk_layer = BasicThunkLayer(
                    cs, fib, pit, faceidtable, thunktable, plantable,
                    self.parser, log_level=log_level)
                self.nfnlayer.optimizer = ThunkPlanExecutor(
                    cs, fib, pit, faceidtable, plantable)
            self.timeoutpreventionlayer = BasicTimeoutPreventionLayer(
                timeoutprevention_dict, comp_table, pit=pit, log_level=log_level)
            if use_thunks:
                self.lstack: LayerStack = LayerStack([
                    self.nfnlayer,
                    self.chunklayer,
                    self.timeoutpreventionlayer,
                    self.thunk_layer,
                    self.icnlayer,
                    self.packetencodinglayer,
                    self.linklayer,
                ])
            else:
                self.lstack: LayerStack = LayerStack([
                    self.nfnlayer,
                    self.chunklayer,
                    self.timeoutpreventionlayer,
                    self.icnlayer,
                    self.packetencodinglayer,
                    self.linklayer,
                ])
            self.mgmt = Mgmt(
                cs, fib, pit, self.linklayer, mgmt_port, self.stop_forwarder,
                log_level=log_level)

        self.icnlayer.cs = cs
        self.icnlayer.fib = fib
        self.icnlayer.pit = pit

    def start_forwarder(self):
        if self.runtime is Runtime.ASYNC:
            raise RuntimeError(
                "NFNForwarder was built with runtime=async; "
                "use await start_forwarder_async()"
            )
        self.lstack.start_all()
        self.icnlayer.ageing()
        self.timeoutpreventionlayer.ageing()
        self.mgmt.start_process()

    def stop_forwarder(self):
        if self.runtime is Runtime.ASYNC:
            raise RuntimeError(
                "NFNForwarder was built with runtime=async; "
                "use await stop_forwarder_async()"
            )
        self.lstack.stop_all()
        if self.mgmt.process:
            self.mgmt.stop_process()
        self.lstack.close_all()

    async def start_forwarder_async(self) -> None:
        if self.runtime is not Runtime.ASYNC:
            raise RuntimeError(
                "NFNForwarder was built with runtime=sync; use start_forwarder()"
            )
        self.lstack.start_all()
        await self.mgmt.start()

    async def stop_forwarder_async(self) -> None:
        if self.runtime is not Runtime.ASYNC:
            raise RuntimeError(
                "NFNForwarder was built with runtime=sync; use stop_forwarder()"
            )
        await self.mgmt.stop()
        await self.lstack.stop_all()
