""" Link Layer Inferface using UDP Sockets for Communication """

from PiCN.Processes import LayerProcess
import multiprocessing, select, socket, time

class UDP4LinkLayer(LayerProcess):
    """ Link Layer Inferface using UDP Sockets for Communication """

    def __init__(self, port: int = 9000, log_level=255, buffersize: int = 8192, max_fids_entries: int = int(1e6)):
        LayerProcess.__init__(self, logger_name="LinkLayer", log_level=log_level)
        #static unsync data
        self._port: int = port
        self._buffersize: int = buffersize
        self._fids_max_entries: int = max_fids_entries

        #Sync data
        manager = multiprocessing.Manager()
        self._cur_fid = manager.Value('i', 0)
        self._fids_to_ip = manager.dict()  #faceid --> (IP,Port)
        self._ip_to_fid = manager.dict() #(IP,Port) --> faceid
        self._fids_timestamps = manager.dict() #faceid --> timestamp, static

        #Network data, used with a reference
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("0.0.0.0", self._port))

    def get_port(self) -> int:
        """Returns port on which the node is running"""
        return int(self.sock.getsockname()[1])

    def data_from_higher(self, to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue, data):
        raise Exception("Link Layer interacts with sockets. Send Data will handle data_from_higher!")

    def data_from_lower(self, to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue, data):
        raise Exception("Link Layer interacts with sockets. There is no lower layer!")

    def stop_process(self):
        self.sock.close()
        if self.process:
            self.process.terminate()
        else:
            pass
        if self.queue_from_lower:
            self.queue_from_lower.close()
        if self.queue_from_higher:
            self.queue_from_higher.close()
        if self.queue_to_lower:
            self.queue_to_lower.close()
        if self.queue_to_higher:
            self.queue_to_higher.close()

    def _run_select(self, from_lower: multiprocessing.Queue, from_higher: multiprocessing.Queue,
            to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue):
        """Requires special handling since there is no lower layer, invokes receive and send data using select"""
        while True:
            in_vars = [self.sock, from_higher._reader]
            ready_vars, _, _ = select.select(in_vars, [], [])
            for var in ready_vars:
                if var == self.sock:
                    self.receive_data(self.sock, to_higher)
                elif var == from_higher._reader:
                    self.send_data(self.sock, from_higher)
                else:
                    pass

    def _run_poll(self, from_lower: multiprocessing.Queue, from_higher: multiprocessing.Queue,
            to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue):
        """Requires special handling since there is no lower layer, invokes receive and send data using poll"""
        poller = select.poll()
        READ_ONLY = select.POLLIN | select.POLLPRI | select.POLLHUP | select.POLLERR
        if self.sock:
            poller.register(self.sock, READ_ONLY)
        if from_higher:
            poller.register(from_higher._reader, READ_ONLY)
        while True:
            ready_vars = poller.poll()
            for filno, var in ready_vars:
                if self.sock and filno == self.sock.fileno():
                    self.receive_data(self.sock, to_higher)
                elif from_higher and filno == from_higher._reader.fileno():
                    self.send_data(self.sock, from_higher)
                else:
                    pass

    def _run_sleep(self, from_lower: multiprocessing.Queue, from_higher: multiprocessing.Queue,
                   to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue):
        """ Process loop, handle incomming packets, use round-robin, required for NT since MS POSIX api do not support
         select on file descriptors nor polling"""
        while True:
            ready_vars = select.select([self.sock], [], [], 0.3)
            for var in ready_vars:
                if var == self.sock:
                    self.receive_data(self.sock, to_higher)
            if from_higher and not from_higher.empty():
                self.send_data(self.sock, from_higher)

    def send_data(self, sock: socket.socket, from_higher: multiprocessing.Queue):
        """Gets data from the higher layer and forwards them to the network"""
        if not from_higher.empty():
            data = from_higher.get()
            if len(data) != 2:
                self.logger.warning("Expexts list of length 2 from higher layer")
                return
            if(type(data[0]) != int):
                self.logger.warning("Expexts first element to be a faceid")
                return
            faceid = data[0]
            packet = data[1]
            addr = self._fids_to_ip.get(faceid)
            if not addr:
                self.logger.warning("Expexts first element to be a valid faceid")
                return
            sock.sendto(packet, addr)
            self.logger.info("Data sent to " + addr[0] + "/" + str(addr[1]))
        else:
            pass

    def receive_data(self, sock: socket.socket, to_higher: multiprocessing.Queue):
        """receive data from the socket and enqueues them with together the faceid: [faceid, data]"""
        if sock:
            data, addr = sock.recvfrom(self._buffersize)
            self.logger.info("Data received from " + addr[0] + "/" + str(addr[1]))
            fid = self.get_or_create_fid(addr)
            to_higher.put([fid, data])
        else:
            pass

    def get_or_create_fid(self, addr, static: bool = False) -> int:
        """Get or Create a new FIDs entry given a link layer address"""
        fid = self._ip_to_fid.get(addr)
        if fid is None:
            fid = self.create_new_fid(addr, static)
        return fid

    def create_new_fid(self, addr, static: bool = False) -> int:
        """Create a new FIDs entry given a link layer address, removes oldest if no space left"""
        self.__clean_fids()
        fid = self._cur_fid.value
        self._fids_to_ip[fid] = addr
        self._ip_to_fid[addr] = fid
        if not static:
            self._fids_timestamps[time.time()] = fid
        self._cur_fid.value = self._cur_fid.value + 1
        return fid

    def __clean_fids(self):
        """Removes the oldest entry from the fid table if there is no space left"""
        if(len(self._fids_timestamps) == 0):
            return
        if(len(self._ip_to_fid) > self._fids_max_entries or len(self._fids_to_ip) > self._fids_max_entries):
            oldest_ts = min(self._fids_timestamps.keys())
            oldest_fid = self._fids_timestamps[oldest_ts]
            oldest_addr = self._fids_to_ip.get(oldest_fid)
            del self._fids_to_ip[oldest_fid]
            del self._ip_to_fid[oldest_addr]
            del self._fids_timestamps[oldest_ts]
        else:
            pass






