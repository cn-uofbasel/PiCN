"""NFN Layer Implementation, containing the NFN Dispatcher
    Queues to Computation ship only the packet, no ID
    Queues to lower layer ship ID and packet
"""

import multiprocessing
import select
import threading
import time
from typing import List, Dict

from PiCN.Processes import LayerProcess
from PiCN.Packets import Interest, Content, Name, Packet, Nack
from PiCN.Layers.ICNLayer.ContentStore import BaseContentStore
from PiCN.Layers.ICNLayer.ForwardingInformationBase import BaseForwardingInformationBase
from PiCN.Layers.ICNLayer.PendingInterestTable import BasePendingInterestTable

from PiCN.Layers.NFNLayer.NFNEvaluator import NFNEvaluator
from PiCN.Layers.NFNLayer.NFNEvaluator.NFNExecutor import BaseNFNExecutor

class BasicNFNLayer(LayerProcess):
    """NFN Layer Implementation"""

    def __init__(self, manager: multiprocessing.Manager, content_store: BaseContentStore,
                 fib: BaseForwardingInformationBase, pit: BasePendingInterestTable,
                 executor: Dict[str, type(BaseNFNExecutor)], logger_name="NFN Layer", debug_level=255):
        super().__init__(logger_name, debug_level)
        self.manager = manager
        self.content_store = content_store
        self.fib = fib
        self.pit = pit
        self._running_computations: Dict[int, NFNEvaluator] = {} # {} #computation id -> computation
        self._computation_request_table: Dict[Name, List[int]] = self.manager.dict()  # request(name) -> [computation id]
        self._pending_computations: multiprocessing.Queue[Interest] = multiprocessing.Queue() # computations not started yet
        self._further_rewirtes_table: Dict[Name, List[Name]] = self.manager.dict() #current rewrite --> next rewrites
        self.rewrite_table: Dict[Name, List[Name]] = self.manager.dict() #rewritten name -> original name
        self.executor: Dict[str, type(BaseNFNExecutor)] = executor

        self._max_running_computations: int = 50
        self._next_computation_id: int = 0
        self._ageing_interval: int = 3
        self._timeout_interal: int = 20
        self.ageing_lock: threading.Lock = threading.Lock()

        self.nfn_evaluator_type = NFNEvaluator

    def data_from_lower(self, to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue, data,
                        running_computations: Dict):
        id = data[0]
        packet = data[1]
        self.logger.info("Handling Packet")
        if isinstance(packet, Interest):
            self.logger.info("Handling Interest " + str(packet.name))
            if packet.name.components[-1] != "NFN":
                to_lower.put([id, packet])
            elif len(packet.name.components) > 2 and packet.name.components[-3] == "R2C":
                self.handle_R2C_interest(packet)
            else:
                self.add_computation(packet, running_computations)
        elif isinstance(packet, Content):
            self.logger.info("Handling Content " + str(packet.name) + " " + str(packet.content))
            if len(packet.name.components) > 2 and packet.name.components[-3] == "R2C":
                self.handle_R2C_content(packet)
            else:
                in_table = False
                if packet.name in self.rewrite_table:
                    in_table = True
                    self.handle_packet_in_rewrite_table(packet, running_computations)
                if packet.name in self._computation_request_table:
                    in_table = True
                    self.handle_packet_in_compuation_request_table(packet, running_computations)
                if not in_table and packet.name.components[-1] != "NFN":
                    to_lower.put([id, packet])
        elif isinstance(packet, Nack):
            self.logger.info("Handling Nack")
            if not self.rewrite_table.get(packet.name):
                self.queue_to_lower.put([id, packet])
                return
            original_packet_names = self.rewrite_table.get(packet.name)
            del self.rewrite_table[packet.name]
            if not self._further_rewirtes_table.get(packet.name):
                #TODO Start Computation here, if no name is left
                #self.queue_to_lower.put([id, packet])
                if packet.name in self._further_rewirtes_table.keys():
                    del self._further_rewirtes_table[packet.name]
                return
            next_names = self._further_rewirtes_table.get(packet.name)
            del self._further_rewirtes_table[packet.name]
            send_names = next_names[0]
            self.queue_to_lower.put([id, Interest(send_names)])
            self.rewrite_table[send_names] = original_packet_names
            self._further_rewirtes_table[send_names] = next_names[1:]

    def data_from_higher(self, to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue, data):
        """empty since there is no higher layer"""
        pass

    def handle_packet_in_compuation_request_table(self, packet, running_computations: Dict):
        """handle computation request table entries"""
        cids = self._computation_request_table[packet.name]
        for cid in cids:
            running_computations[cid].start_time = time.time()
            running_computations[cid].computation_in_queue.put(packet)
        del self._computation_request_table[packet.name]

    def handle_packet_in_rewrite_table(self, packet, running_computations: Dict):
        """handle computation request table entries"""
        original_names = self.rewrite_table[packet.name]
        for on in original_names:
            cid = 0
            mapped_back_content = Content(on, packet.content)
            if(on in self._computation_request_table):
                cids = self._computation_request_table[on]
                for cid in cids:
                    self._running_computations[cid].computation_in_queue.put(mapped_back_content)
            self.queue_to_lower.put([cid, mapped_back_content]) #TODO, avoid this if not necessary? cid=-1?
        #stop computation
        if self._computation_request_table.get(packet.name):
            waiting_comp_ids = self._computation_request_table[packet.name]
            remove_ids = []
            for cid in waiting_comp_ids:
                if running_computations[cid].interest.name == packet.name:
                    running_computations[cid].stop_process()
                    remove_ids.append(cid)
            for cid in remove_ids:
                del running_computations[cid]

    def ageing(self, running_computations: Dict):
        """perform the aging operations for the NFN Layer
           perfom the timeout prevention
           """
        try:
            self.logger.debug("Ageing NFN")
            self.handle_computation_timeouts(running_computations)
            self.handle_pending_computation_queue(running_computations)
            t = threading.Timer(self._ageing_interval, self.ageing, args=[running_computations])
            t.setDaemon(True)
            t.start()
        except:
            pass
        pass

    def add_computation(self, interest: Interest, running_computations: Dict):
        """add a computation to the list of pending computations"""
        if len(running_computations.keys()) > self._max_running_computations:
            self._pending_computations.put(interest)
        else:
            self.start_computation(interest, running_computations)

    def start_computation_queue_handler(self, running_computations: Dict):
        """start a new thread to run the computation queue handler"""
        t = threading.Thread(target=self.handle_computation_queue, args=[running_computations])
        t.setDaemon(True)
        t.start()

    def handle_computation_queue(self, running_computations: Dict):
        """check the computation queues use a poller, this must be executed in a thread
        (use start_computation_queue_handler)"""
        while True:
            poller = select.poll()
            READ_ONLY = select.POLLIN | select.POLLPRI | select.POLLHUP | select.POLLERR
            if len(running_computations.keys()) == 0:
                continue
            for cid in running_computations.keys():
                comp = running_computations[cid]
                poller.register(comp.computation_out_queue._reader, READ_ONLY)
            ready_vars = poller.poll(0.1)
            for filno, var in ready_vars:
                new_comps = []
                stop_comps = []
                for cid in running_computations.keys():
                    comp = running_computations[cid]
                    if filno == comp.computation_out_queue._reader.fileno() and not comp.computation_out_queue.empty():
                        while not comp.computation_out_queue.empty():
                            packet = comp.computation_out_queue.get()
                            self.handle_packet_from_computation_queues(cid, packet, running_computations,
                                                                       new_comps, stop_comps)
                for nc in new_comps:
                    self.add_computation(nc, running_computations)
                for scid in stop_comps:
                    self.stop_computation(scid, running_computations)

    def handle_packet_from_computation_queues(self, cid: int, packet: Packet, running_computations: Dict,
                                              new_comps: List, stop_comps: List):
        """handle an incomming packet from a computation process"""
        if isinstance(packet, List):  # Rewritten packet
            if packet[0].name in self.rewrite_table:
                self.queue_to_lower.put([cid, packet[0]])
                names = [p.name for p in packet]
                self._further_rewirtes_table[packet[0].name] = names[1:]
        elif isinstance(packet, Interest):
            if (packet.name in self._computation_request_table):
                self._computation_request_table[packet.name].append(cid)
            else:
                if packet.name.components[-1] == "NFN":
                    new_comps.append(packet)
                    self._computation_request_table[packet.name] = [cid]
                    return
                else:
                    self._computation_request_table[packet.name] = [cid]
            self.queue_to_lower.put([cid, packet])
        elif isinstance(packet, Content):
            waiting_cids = self._computation_request_table.get(packet.name)
            if waiting_cids is None:
                self.queue_to_lower.put([cid, packet])
            else:
                for wc in waiting_cids:
                    running_computations[wc].computation_in_queue.put(packet)
            stop_comps.append(cid)
        elif isinstance(packet, Nack):
            self.queue_to_lower.put([cid, packet])
            stop_comps.append(cid)

    def stop_computation(self, cid: int, running_computations: Dict):
        """Stop a running computation"""
        running_computations[cid].stop_process()
        del running_computations[cid]

    def handle_computation_timeouts(self, running_computations: Dict):
        """handle the timeouts of the computation"""
        #todo
        pass

    def handle_pending_computation_queue(self, running_computations: Dict):
        """execute a computation if there are capacities"""
        self.ageing_lock.acquire()
        num_running_computations = len(running_computations.keys())
        if(num_running_computations > self._max_running_computations):
            self.ageing_lock.release()
            return
        else:

            while((not self._pending_computations.empty())
                  and (len(running_computations.keys()) < self._max_running_computations)):
                interest = self._pending_computations.get()
                self.start_computation(interest, running_computations)
            self.ageing_lock.release()

    def start_computation(self, interest, running_computations):
        evaluator = self.nfn_evaluator_type(interest, self.content_store, self.fib, self.pit,
                                            self.rewrite_table, self.executor, self.logger.level)
        running_computations[self._next_computation_id] = evaluator
        running_computations[self._next_computation_id].start_process()
        self._next_computation_id = self._next_computation_id + 1

    def request_data(self, computation_id):
        """request data for a computation"""
        #TODO
        pass

    def handle_R2C_interest(self, interest: Interest, running_computations: Dict):
        """Handle the R2C Mesasges Content"""
        if interest.name not in self._computation_request_table:
            return
        cid = self._computation_request_table[interest.name]
        if interest.name.components[-2] == "STOP":
            #TODO , check no one else awaits result
            self.stop_computation(cid)
            #TODO , send reply message
        pass

    def handle_R2C_content(self, content: Content, running_computations: Dict):
        """Handle the R2C Mesasges Content"""
        #TODO handle r2c content
        pass

    def start_process(self):
        self.process = multiprocessing.Process(target=self._run_nfn_layer, args=[self._queue_from_lower,
                                                                       self._queue_from_higher,
                                                                       self._queue_to_lower,
                                                                       self._queue_to_higher,
                                                                       self._running_computations])
        self.process.start()

    def stop_process(self):
        if self.process:
            self.process.terminate()


    def _run_nfn_layer(self, from_lower: multiprocessing.Queue, from_higher: multiprocessing.Queue,
                  to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue, running_computations: Dict):
        """ Process loop, handle incomming packets, use poll if many file descripors are required"""
        self.start_computation_queue_handler(running_computations)
        self.ageing(running_computations)
        poller = select.poll()
        READ_ONLY = select.POLLIN | select.POLLPRI | select.POLLHUP | select.POLLERR
        if from_lower:
            poller.register(from_lower._reader, READ_ONLY)
        if from_higher:
            poller.register(from_higher._reader, READ_ONLY)
        while True:
            ready_vars = poller.poll()
            for filno, var in ready_vars:
                if from_lower and filno == from_lower._reader.fileno() and not from_lower.empty():
                    self.data_from_lower(to_lower, to_higher, from_lower.get(), running_computations)
                elif from_higher and filno == from_higher._reader.fileno() and not from_higher.empty():
                    self.data_from_higher(to_lower, to_higher, from_higher.get())
