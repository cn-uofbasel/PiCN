"""Mgmt System for PiCN"""

import multiprocessing
import os
import select
import socket
import time
from typing import Dict

from PiCN.Layers.ICNLayer.ContentStore import BaseContentStore
from PiCN.Layers.ICNLayer.ForwardingInformationBase import BaseForwardingInformationBase

from PiCN.Layers.ICNLayer.PendingInterestTable import BasePendingInterestTable
from PiCN.Packets import Content, Name
from PiCN.Processes import LayerProcess
from PiCN.Processes import PiCNProcess
from PiCN.Layers.LinkLayer.Interfaces import AddressInfo, BaseInterface, UDP4Interface


class Mgmt(PiCNProcess):
    """Mgmt System for PiCN"""

    def __init__(self, cs: BaseContentStore, fib: BaseForwardingInformationBase, pit:BasePendingInterestTable,
                 linklayer: LayerProcess, port: int, shutdown = None,
                 repo_prfx: str=None, repo_path: str=None, log_level=255):
        super().__init__("MgmtSys", log_level)
        self.cs = cs
        self.fib = fib
        self.pit = pit
        self._linklayer = linklayer

        self._repo_prfx = repo_prfx
        self._repo_path = repo_path
        self._port: int = port

        # init MGMT
        self.mgmt_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.mgmt_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.mgmt_sock.bind(("127.0.0.1", self._port))
        self.mgmt_sock.listen(5)
        self._buffersize = 8192
        if os.name is not 'nt':
            self.shutdown = shutdown #function pointer
        else:
            self.logger.critical("Shutdown not available on NT platform")

    def mgmt(self, mgmt_sock):
        """parse mgmt message"""
        replysock, addr = mgmt_sock.accept()

        try:
            # receive data
            data = replysock.recv(self._buffersize)
            request_string = data.decode()
            # Parse HTTP
            fields = request_string.split("\r\n")
            request: str = fields[0]
            fields = fields[1:]
            type, name = request.split(" ", 1)
            httpversion = request.rsplit(" ", 1)[-1]

            http = {}
            for field in fields:
                if (len(field.split(":")) == 2):
                    key, value = field.split(':', 1)
                    http[key] = value

            # Execute MGMT
            name = name.replace(" HTTP/1.1", "")
            mgmt_request = name.split("/")
            if (len(mgmt_request) == 4):
                layer = mgmt_request[1]
                command = mgmt_request[2]
                params = mgmt_request[3]
                if (layer == "linklayer"):
                    self.ll_mgmt(command, params, replysock)
                elif(layer == "icnlayer"):
                    self.icnl_mgmt(command, params, replysock)
                elif(layer == "repolayer"):
                    self.repol_mgmt(command, params, replysock)
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
            ip, port, if_num = params.split(":", 2)
            if port != 'None':
                port = int(port)
            if_num = int(if_num)
            if port != 'None':
                fid = self._linklayer.faceidtable.get_or_create_faceid(AddressInfo((ip, port), if_num))
            else:
                fid = self._linklayer.faceidtable.get_or_create_faceid(AddressInfo(ip, if_num))
            reply = "HTTP/1.1 200 OK \r\n Content-Type: text/html \r\n\r\n newface OK:" + str(fid) + "\r\n"
            replysock.send(reply.encode())
            self.logger.info("New Face added " + ip + "|" + str(port) + ", FaceID: " + str(fid))
        else:
            self.unknown_command(replysock)
            return

    def icnl_mgmt(self, command, params, replysock):
        if(self.cs == None or self.fib == None or
                self.pit== None):
            reply = "HTTP/1.1 200 OK \r\n Content-Type: text/html \r\n\r\n Not a Forwarder OK\r\n"
            replysock.send(reply.encode())
        # newface expects /linklayer/newface/ip:port
        elif (command == "newforwardingrule"):
            prefix, faceid = params.split(":", 1)
            faceid = int(faceid)
            prefix = prefix.replace("%2F", "/")
            name = Name(prefix)
            self.fib.add_fib_entry(name, faceid, True)
            reply = "HTTP/1.1 200 OK \r\n Content-Type: text/html \r\n\r\n newforwardingrule OK:" + str(faceid) + "\r\n"
            replysock.send(reply.encode())
            self.logger.info("New Forwardingrule added " + prefix + "|" + str(faceid))
            return
        elif(command == "newcontent"):
            prefix, content = params.split(":", 1)
            prefix = prefix.replace("%2F", "/")
            name = Name(prefix)
            content = Content(name, content)
            self.cs.add_content_object(content, static=True)
            reply = "HTTP/1.1 200 OK \r\n Content-Type: text/html \r\n\r\n newcontent OK\r\n"
            replysock.send(reply.encode())
            self.logger.info("New content added " + prefix + "|" + content.content)
            return
        else:
            self.unknown_command(replysock)
            return

    def repol_mgmt(self, command, params, replysock):
        if(self._repo_path == None or self._repo_prfx == None):
            reply = "HTTP/1.1 200 OK \r\n Content-Type: text/html \r\n\r\n Not a Repo OK\r\n"
            replysock.send(reply.encode())
        elif(command == "getprefix"):
            reply = "HTTP/1.1 200 OK \r\n Content-Type: text/html \r\n\r\n " + str(self._repo_prfx) + " OK\r\n"
            replysock.send(reply.encode())
        elif(command =="getpath"):
            abs_path = os.path.abspath(str(self._repo_path))
            reply = "HTTP/1.1 200 OK \r\n Content-Type: text/html \r\n\r\n " + str(abs_path) + " OK\r\n"
            replysock.send(reply.encode())
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

    def _run_poll(self, mgmt_sock):
        poller = select.poll()
        READ_ONLY = select.POLLIN | select.POLLPRI | select.POLLHUP | select.POLLERR
        poller.register(mgmt_sock, READ_ONLY)
        while True:
            ready_vars = poller.poll()
            self.mgmt(mgmt_sock)

    def _run(self, mgmt_sock):
        if os.name is 'nt':
            self._run_select(mgmt_sock)
        else:
            self._run_poll(mgmt_sock)

    def start_process(self):
        self.process = multiprocessing.Process(target=self._run, args=[self.mgmt_sock])
        self.process.start()

    def stop_process(self):
        if self.process:
            self.process.terminate()
            self.process = None
        self.mgmt_sock.close()

