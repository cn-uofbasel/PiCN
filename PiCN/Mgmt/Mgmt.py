"""Mgmt System for PiCN"""

import multiprocessing
import select
import socket
import time

from PiCN.Layers.ICNLayer.ContentStore import BaseContentStore
from PiCN.Layers.ICNLayer.ForwardingInformationBase import BaseForwardingInformationBase

from PiCN.Layers.ICNLayer.PendingInterestTable import BasePendingInterestTable
from PiCN.Packets import Content, Name
from PiCN.Processes import LayerProcess
from PiCN.Processes import PiCNProcess


class Mgmt(PiCNProcess):
    """Mgmt System for PiCN"""

    def __init__(self, cs: BaseContentStore, fib: BaseForwardingInformationBase, pit: BasePendingInterestTable,
                 linklayer: LayerProcess, port: int, shutdown = None, debug_level=255):
        super().__init__("MgmtSys", debug_level)
        self._cs: BaseContentStore = cs
        self._fib: BaseForwardingInformationBase = fib
        self._pit: BasePendingInterestTable = pit
        self._linklayer: LayerProcess = linklayer
        self._port: int = port

        # init MGMT
        self.mgmt_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.mgmt_sock.bind(("127.0.0.1", self._port))
        self.mgmt_sock.listen(5)
        self._buffersize = 8192
        self.shutdown = shutdown #function pointer

    def mgmt(self, mgmt_sock):
        """parse mgmt message"""
        replysock, addr = mgmt_sock.accept()

        try:
            # receive data
            data = replysock.recv(self._buffersize)
            request_string = data.decode()
            # Parse HTTP
            fields = request_string.split("\r\n")
            request = fields[0]
            fields = fields[1:]
            type, name, httpversion = request.split(" ", 3)
            http = {}
            for field in fields:
                if (len(field.split(":")) == 2):
                    key, value = field.split(':')
                    http[key] = value

            # Execute MGMT
            mgmt_request = name.split("/")
            if (len(mgmt_request) == 4):
                layer = mgmt_request[1]
                command = mgmt_request[2]
                params = mgmt_request[3]
                if (layer == "linklayer"):
                    self.ll_mgmt(command, params, replysock)
                elif(layer == "icnlayer"):
                    self.icnl_mgmt(command, params, replysock)
            elif len(mgmt_request) == 2:
                if mgmt_request[1] == "shutdown":
                    self.logger.info("Shutdown")
                    replysock.send("HTTP/1.1 200 OK \r\n Content-Type: text/html \r\n\r\n shutdown\r\n".encode())
                    replysock.close()
                    time.sleep(2)
                    self.shutdown()
        finally:
            replysock.close()

    def ll_mgmt(self, command, params, replysock):
        # newface expects /linklayer/newface/ip:port
        if (command == "newface"):
            ip, port = params.split(":")
            port = int(port)
            fid = self._linklayer.get_or_create_fid((ip, port), static=True)
            reply = "HTTP/1.1 200 OK \r\n Content-Type: text/html \r\n\r\n newface OK:" + str(fid) + "\r\n"
            replysock.send(reply.encode())
            self.logger.info("New Face added " + ip + "|" + str(port) + ", FaceID: " + str(fid))
        else:
            self.unknown_command(replysock)
            return

    def icnl_mgmt(self, command, params, replysock):
        # newface expects /linklayer/newface/ip:port
        if (command == "newforwardingrule"):
            prefix, faceid = params.split(":")
            faceid = int(faceid)
            prefix = prefix.replace("%2F", "/")
            name = Name(prefix)
            self._fib.add_fib_entry(name, faceid, True)
            reply = "HTTP/1.1 200 OK \r\n Content-Type: text/html \r\n\r\n newforwardingrule OK:" + str(faceid) + "\r\n"
            replysock.send(reply.encode())
            self.logger.info("New Forwardingrule added " + prefix + "|" + str(faceid))
            return
        elif(command == "newcontent"):
            prefix, content = params.split(":")
            prefix = prefix.replace("%2F", "/")
            name = Name(prefix)
            content = Content(name, content)
            self._cs.add_content_object(content, static=True)
            reply = "HTTP/1.1 200 OK \r\n Content-Type: text/html \r\n\r\n newcontent OK\r\n"
            replysock.send(reply.encode())
            self.logger.info("New content added " + prefix + "|" + content.content)
            return
        else:
            self.unknown_command(replysock)
            return

    def unknown_command(self, replysock):
        reply = "HTTP/1.1 200 OK \r\n Content-Type: text/html \r\n\r\n Unknown Command\r\n"
        replysock.send(reply.encode())

    def _run_select(self, mgmt_sock):
        while True:
            socks = [mgmt_sock]
            ready_vars, _, _ = select.select(socks, [], [])
            self.mgmt(mgmt_sock)

    def _run(self, mgmt_sock):
        poller = select.poll()
        READ_ONLY = select.POLLIN | select.POLLPRI | select.POLLHUP | select.POLLERR
        poller.register(mgmt_sock, READ_ONLY)
        while True:
            ready_vars = poller.poll()
            self.mgmt(mgmt_sock)

    def start_process(self):
        self.process = multiprocessing.Process(target=self._run, args=[self.mgmt_sock])
        self.process.start()

    def stop_process(self):
        if self.process:
            self.process.terminate()
            self.process = None
        self.mgmt_sock.close()

