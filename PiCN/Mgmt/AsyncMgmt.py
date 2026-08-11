"""Async management TCP server for PiCN (Phase 5).

Same HTTP request/reply semantics as :class:`PiCN.Mgmt.Mgmt.Mgmt`, but
served via ``asyncio.start_server`` in the node event loop -- no
``multiprocessing.Process``, ``terminate()``, or ``time.sleep``. See
ADR-006's 2026-08-04 AsyncMgmt addendum.
"""

import asyncio
import inspect
from typing import Awaitable, Callable, Optional, Union

from PiCN.Layers.ICNLayer.ContentStore import BaseContentStore
from PiCN.Layers.ICNLayer.ForwardingInformationBase import BaseForwardingInformationBase
from PiCN.Layers.ICNLayer.PendingInterestTable import BasePendingInterestTable
from PiCN.Layers.LinkLayer.Interfaces import AddressInfo
from PiCN.Logger import Logger
from PiCN.Packets import Content, Name
from PiCN.Processes.AsyncLayerProcess import SHUTDOWN_TIMEOUT

ShutdownCallback = Union[
    Callable[[], None],
    Callable[[], Awaitable[None]],
]


class AsyncMgmt(object):
    """asyncio TCP management server with characterized Mgmt HTTP semantics.

    :param cs: content store (may be None for non-forwarder nodes)
    :param fib: FIB (may be None)
    :param pit: PIT (may be None)
    :param linklayer: object with ``.interfaces`` and ``.faceidtable``
    :param port: listen port on 127.0.0.1
    :param shutdown: optional sync or async callable invoked on /shutdown
        (no sleep before the call; callers must avoid re-entering
        :meth:`stop` from the same task -- prefer ``create_task`` /
        event signalling at the ProgramLib level)
    :param repo_prfx: optional repository prefix for repolayer commands
    :param repo_path: optional repository path for repolayer commands
    :param log_level: logger level
    """

    def __init__(
        self,
        cs: BaseContentStore,
        fib: BaseForwardingInformationBase,
        pit: BasePendingInterestTable,
        linklayer,
        port: int,
        shutdown: Optional[ShutdownCallback] = None,
        repo_prfx: str = None,
        repo_path: str = None,
        log_level: int = 255,
    ):
        self.logger = Logger("AsyncMgmt", log_level)
        self.cs = cs
        self.fib = fib
        self.pit = pit
        self._linklayer = linklayer
        self._repo_prfx = repo_prfx
        self._repo_path = repo_path
        self._port = port
        self.shutdown = shutdown
        self._buffersize = 8192
        self._server: Optional[asyncio.Server] = None
        self._serve_task: Optional[asyncio.Task] = None

    @property
    def port(self) -> int:
        return self._port

    async def start(self) -> None:
        """Start listening on 127.0.0.1:port. Must run in an event loop."""
        if self._server is not None:
            return
        self._server = await asyncio.start_server(
            self._handle_client, "127.0.0.1", self._port)
        # port=0 -> OS-assigned ephemeral port (matches sync Mgmt.bind behaviour)
        if self._server.sockets:
            self._port = self._server.sockets[0].getsockname()[1]
        self._serve_task = asyncio.create_task(
            self._server.serve_forever(), name="AsyncMgmt-serve")

    async def stop(self, timeout: float = SHUTDOWN_TIMEOUT) -> None:
        """Close the listening socket and cancel the serve task (ADR-006)."""
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
        if self._serve_task is not None:
            self._serve_task.cancel()
            done, pending = await asyncio.wait(
                [self._serve_task], timeout=timeout)
            if pending:
                self.logger.warning(
                    "AsyncMgmt.stop() timed out after %.1fs; serve task "
                    "did not stop", timeout,
                )
            self._serve_task = None

    async def _handle_client(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        try:
            data = await reader.read(self._buffersize)
            request_string = data.decode()
            reply = await self._dispatch(request_string)
            if reply is not None:
                writer.write(reply.encode())
                await writer.drain()
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass

    async def _dispatch(self, request_string: str) -> Optional[str]:
        """Parse one HTTP request and return the reply body, or None."""
        fields = request_string.split("\r\n")
        request: str = fields[0]
        name = request.split(" ", 1)[1] if " " in request else ""
        name = name.replace(" HTTP/1.1", "")
        mgmt_request = name.split("/")

        if len(mgmt_request) == 4:
            layer = mgmt_request[1]
            command = mgmt_request[2]
            params = mgmt_request[3]
            if layer == "linklayer":
                return self._ll_mgmt(command, params)
            if layer == "icnlayer":
                return self._icnl_mgmt(command, params)
            if layer == "repolayer":
                return self._repol_mgmt(command, params)
            return self._unknown_command()

        if len(mgmt_request) == 2 and mgmt_request[1] == "shutdown":
            self.logger.info("Shutdown")
            reply = (
                "HTTP/1.1 200 OK \r\n Content-Type: text/html \r\n\r\n "
                "shutdown\r\n"
            )
            await self._invoke_shutdown()
            return reply

        return self._unknown_command()

    async def _invoke_shutdown(self) -> None:
        """Fire the shutdown callback without time.sleep (ADR-006)."""
        if self.shutdown is None:
            return
        if inspect.iscoroutinefunction(self.shutdown):
            # Schedule rather than await: ProgramLib stop typically awaits
            # AsyncMgmt.stop(), which would deadlock if we awaited here.
            asyncio.create_task(self.shutdown())
            return
        result = self.shutdown()
        if inspect.isawaitable(result):
            asyncio.create_task(result)

    def _ll_mgmt(self, command: str, params: str) -> str:
        if command == "newface":
            ip, port, if_num = params.split(":", 2)
            if port != "None":
                port = int(port)
            if_num = int(if_num)

            if if_num >= len(self._linklayer.interfaces):
                return f"Interface Number {if_num} does not exit on node"

            if port != "None":
                fid = self._linklayer.faceidtable.get_or_create_faceid(
                    AddressInfo((ip, port), if_num))
            else:
                fid = self._linklayer.faceidtable.get_or_create_faceid(
                    AddressInfo(ip, if_num))
            reply = (
                "HTTP/1.1 200 OK \r\n Content-Type: text/html \r\n\r\n "
                "newface OK:" + str(fid) + "\r\n"
            )
            self.logger.info(
                "New Face added " + ip + "|" + str(port)
                + ", FaceID: " + str(fid)
            )
            return reply
        return self._unknown_command()

    def _icnl_mgmt(self, command: str, params: str) -> str:
        if self.cs is None or self.fib is None or self.pit is None:
            return (
                "HTTP/1.1 200 OK \r\n Content-Type: text/html \r\n\r\n "
                "Not a Forwarder OK\r\n"
            )
        if command == "newforwardingrule":
            prefix, faceid = params.split(":", 1)
            faceid_str = faceid
            faceid = faceid.split(",")
            faceid = list(map(lambda x: int(x), faceid))
            prefix = prefix.replace("%2F", "/")
            name = Name(prefix)
            self.fib.add_fib_entry(name, faceid, True)
            reply = (
                "HTTP/1.1 200 OK \r\n Content-Type: text/html \r\n\r\n "
                "newforwardingrule OK:" + str(faceid_str) + "\r\n"
            )
            self.logger.info(
                "New Forwardingrule added " + prefix + "|" + str(faceid))
            return reply
        if command == "newcontent":
            prefix, content = params.split(":", 1)
            prefix = prefix.replace("%2F", "/")
            name = Name(prefix)
            content_obj = Content(name, content)
            self.cs.add_content_object(content_obj, static=True)
            reply = (
                "HTTP/1.1 200 OK \r\n Content-Type: text/html \r\n\r\n "
                "newcontent OK\r\n"
            )
            self.logger.info(
                "New content added " + prefix + "|" + content_obj.content)
            return reply
        return self._unknown_command()

    def _repol_mgmt(self, command: str, params: str) -> str:
        import os
        if self._repo_path is None or self._repo_prfx is None:
            return (
                "HTTP/1.1 200 OK \r\n Content-Type: text/html \r\n\r\n "
                "Not a Repo OK\r\n"
            )
        if command == "getprefix":
            return (
                "HTTP/1.1 200 OK \r\n Content-Type: text/html \r\n\r\n "
                + str(self._repo_prfx) + " OK\r\n"
            )
        if command == "getpath":
            abs_path = os.path.abspath(str(self._repo_path))
            return (
                "HTTP/1.1 200 OK \r\n Content-Type: text/html \r\n\r\n "
                + str(abs_path) + " OK\r\n"
            )
        return self._unknown_command()

    def _unknown_command(self) -> str:
        return (
            "HTTP/1.1 200 OK \r\n Content-Type: text/html \r\n\r\n "
            "Unknown Command\r\n"
        )
