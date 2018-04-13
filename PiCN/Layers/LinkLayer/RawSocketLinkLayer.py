""" Link Layer Inferface using RAW Sockets for Communication """

from PiCN.Processes import LayerProcess
import multiprocessing, select, socket, time, AF_PACKET, SOCK_RAW, htonl

class EthernetLinkLayer(LayerProcess):
    """ Link Layer Inferface using RAW Sockets for Communication """

    def __init__(self, address: str = "", buffersize: int = 1500, max_fids_entries: int = int(1e6),
                 manager: multiprocessing.Manager=None, log_level=255):
        LayerProcess.__init__(self, logger_name="LinkLayer", log_level=log_level)
        #static unsync data
        self.address: str = address
        self._buffersize: int = buffersize
        self._fids_max_entries: int = max_fids_entries

        #Sync data
        if manager is None:
            manager = multiprocessing.Manager()
        self._cur_fid = manager.Value('i', 0)
        self._fids_to_address = manager.dict()  #faceid --> (MAC addr)
        self._address_to_fid = manager.dict() #(MAC addr) --> faceid
        self._fids_timestamps = manager.dict() #faceid --> timestamp, static

        #Network data, used with a reference
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_RAW)
        # TODO check address format
        self.sock.bind(("", 0))     # TODO address: is it a Broadcast, Multicast or Unicast?

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

    # TODO implement _run_select
    # TODO implement _run_poll
    # TODO implement _run_sleep

    def send_data(self, sock: socket.socket, from_higher: multiprocessing.Queue):
        """Gets data from the higher layer and forwards them to the network"""
        if not from_higher.empty():
            data = from_higher.get()
            if len(data) != 2:
                self.logger.warning("Expects list of length 2 from higher layer")
                return
            if(type(data[0]) != int):
                self.logger.warning("Expects first element to be a faceid")
                return
            faceid = data[0]
            packet = data[1]
            addr = self._fids_to_address.get(faceid)
            if not addr:
                self.logger.warning("Expects first element to be a valid faceid")
                return
            sock.sendto(packet)
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
        fid = self._address_to_fid.get(addr)
        if fid is None:
            fid = self.create_new_fid(addr, static)
        return fid

    def create_new_fid(self, addr, static: bool = False) -> int:
        """Create a new FIDs entry given a link layer address, removes oldest if no space left"""
        self.__clean_fids()
        fid = self._cur_fid.value
        self._fids_to_address[fid] = addr
        self._address_to_fid[addr] = fid
        if not static:
            self._fids_timestamps[time.time()] = fid
        self._cur_fid.value = self._cur_fid.value + 1
        return fid

    def __clean_fids(self):
        """Removes the oldest entry from the fid table if there is no space left"""
        if(len(self._fids_timestamps) == 0):
            return
        if(len(self._address_to_fid) > self._fids_max_entries or len(self._fids_to_address) > self._fids_max_entries):
            oldest_ts = min(self._fids_timestamps.keys())
            oldest_fid = self._fids_timestamps[oldest_ts]
            oldest_addr = self._fids_to_address.get(oldest_fid)
            del self._fids_to_address[oldest_fid]
            del self._address_to_fid[oldest_addr]
            del self._fids_timestamps[oldest_ts]
        else:
            pass

    # TODO construct ethernet frame
    # TODO checksum create
    # TODO checksum check