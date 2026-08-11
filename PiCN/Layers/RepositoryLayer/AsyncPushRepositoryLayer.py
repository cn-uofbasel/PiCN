"""Async Push Repository Layer (Phase 5.5).

Mirrors PushRepositoryLayer HTTP/NFN publish semantics with asyncio.Queue.
"""

import asyncio
import base64

from PiCN.Layers.ICNLayer.ContentStore import BaseContentStore
from PiCN.Layers.NFNLayer.Parser import DefaultNFNParser
from PiCN.Layers.NFNLayer.Parser.AST import AST_FuncCall, AST_Name, AST_String
from PiCN.Layers.RepositoryLayer.PushRepositoryLayer import is_publish_expression
from PiCN.Packets import Packet, Interest, Nack, NackReason, Content
from PiCN.Processes.AsyncLayerProcess import AsyncLayerProcess


class AsyncPushRepositoryLayer(AsyncLayerProcess):
    """Async counterpart to :class:`PushRepositoryLayer`."""

    def __init__(self, cs: BaseContentStore = None, log_level: int = 255):
        super().__init__(logger_name="PushRepoLyr", log_level=log_level)
        self.cs = cs

    async def data_from_higher(self, to_lower, to_higher, data) -> None:
        pass

    async def data_from_lower(self, to_lower, to_higher, data) -> None:
        if len(data) != 2:
            self.logger.warning(
                "PushRepo Layer expects to receive [face_id, Interest] from lower layer")
            return
        if type(data[0]) != int:
            self.logger.warning(
                "PushRepo Layer expects to receive [face_id, Interest] from lower layer")
            return
        if not isinstance(data[1], Packet):
            self.logger.warning(
                "PushRepo Layer expects to receive [face_id, Interest] from lower layer. Drop.")
            return
        await self._handle_interest_from_lower(data[0], data[1], to_lower)

    async def _handle_interest_from_lower(
        self, face_id: int, interest: Interest, to_lower: asyncio.Queue,
    ) -> None:
        self.logger.info("Incoming interest: " + interest.name.to_string())
        if interest.name.string_components[-1] == "NFN":
            try:
                parser = DefaultNFNParser()
                nfn_str, prepended_name = parser.network_name_to_nfn_str(interest.name)
                ast = parser.parse(nfn_str)
                if is_publish_expression(ast):
                    data_name = ast.params[0]._element
                    payload = ast.params[1]._element
                    try:
                        payload = base64.b64decode(payload[7:])
                        self.logger.info("Payload is base64 encoded. Decoded.")
                    except Exception:
                        self.logger.info(
                            "Invalid publish expression. The payload could not be decoded.")
                        nack = Nack(
                            interest.name, reason=NackReason.COMP_NOT_PARSED,
                            interest=interest)
                        await to_lower.put([face_id, nack])
                        return

                    self.cs.add_content_object(Content(data_name, payload))
                    self.logger.info("Add to database: " + data_name)
                    confirmation = Content(interest.name, "ok")
                    await to_lower.put([face_id, confirmation])
                else:
                    self.logger.info("Invalid publish expression. Wrong format.")
                    nack = Nack(
                        interest.name, reason=NackReason.COMP_NOT_PARSED,
                        interest=interest)
                    await to_lower.put([face_id, nack])
            except Exception:
                self.logger.info("Invalid publish expression.")
                nack = Nack(
                    interest.name, reason=NackReason.COMP_NOT_PARSED,
                    interest=interest)
                await to_lower.put([face_id, nack])
        else:
            db_entry = self.cs.find_content_object(interest.name)
            if db_entry is not None:
                self.logger.info("Found in database")
                await to_lower.put([face_id, db_entry.content])
            else:
                self.logger.info("Not found in database")
                nack = Nack(interest.name, NackReason.NO_CONTENT, interest)
                await to_lower.put([face_id, nack])
