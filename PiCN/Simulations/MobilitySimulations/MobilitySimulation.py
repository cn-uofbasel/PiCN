"""Parametrized mobility simulation"""

import time
import logging

from typing import List

from PiCN.ProgramLibs.Fetch import Fetch
from PiCN.ProgramLibs.ICNForwarder import ICNForwarder
from PiCN.Mgmt import MgmtClient
from PiCN.Logger import Logger
from PiCN.Layers.LinkLayer.Interfaces import AddressInfo
from PiCN.Packets import Name, Content
from PiCN.Layers.NFNLayer.NFNOptimizer.ToDataFirstOptimizer import ToDataFirstOptimizer
from PiCN.Layers.NFNLayer.NFNOptimizer.EdgeComputingOptimizer import EdgeComputingOptimizer
from PiCN.Layers.PacketEncodingLayer.Encoder import SimpleStringEncoder
from PiCN.Layers.LinkLayer.Interfaces import SimulationBus
from PiCN.ProgramLibs.NFNForwarder.NFNForwarder import NFNForwarder
from PiCN.ProgramLibs.NFNForwarder.NFNForwarderData import NFNForwarderData
from PiCN.Simulations.MobilitySimulations.Model.MobileNode import MobileNode
from PiCN.Simulations.MobilitySimulations.Model.StationaryNode import StationaryNode
from PiCN.Simulations.MobilitySimulations.Helper.ConsumerDistributionHelper import ZipfMandelbrotDistribution


class MobilitySimulation(object):
    """This simulation setup is used to simulate a set of mobile nodes within a NFN based infrastructure"""

    def __init__(self, run_id: int, mobile_nodes: List[MobileNode], stationary_nodes: List[StationaryNode],
                 stationary_node_distance: float, named_functions: dict, function_names: list,
                 forwarder: str = "NFNForwarder", optimizer: str = "ToDataFirstOptimizer",
                 use_distribution_helper: bool = False, log_level=logging.DEBUG):
        """
        Configuration of the mobility simulation

        :param run_id the identifier of the simulation run
        :param mobile_nodes a list of mobile nodes part of the simulation
        :param stationary_nodes a list of stationary nodes forming the infrastructure
        :param stationary_node_distance the distance between the stationary nodes
        :param named_functions a dictionary of named function definitions used to be executed
        :param function_names a list of function names to be assigned to the mobile nodes
        :param forwarder the NFN forwarder to be used
        :param optimizer the NFN resolution strategy optimizer to be used in the simulation
        :param use_distribution_helper A flag indicating if the default distribution helper (ZipfMandelbrotDistribution)
        shall be used or not; default = False,
        :param log_level the log level of the logger to be used; default: logging.DEBUG
        """
        self._run_id = run_id
        self._forwarder = forwarder
        self._optimizer = optimizer
        self._mobile_nodes = mobile_nodes
        self._stationary_nodes = stationary_nodes
        self._stationary_node_distance = stationary_node_distance
        self.logger = Logger("MobilitySimulation", log_level)
        self.to_car_faces = [[0] * len(self._mobile_nodes) for i in range(len(self._stationary_nodes))]  # rsu, car -> faceid
        self.to_rsu_faces = [[0] * len(self._mobile_nodes) for i in range(len(self._stationary_nodes))]  # rsu, car -> faceid
        self._velocities = []
        self._heading_directions = []
        self._starting_points = []
        for node in self._mobile_nodes:
            self._velocities.append(node.speed)
            self._heading_directions.append(node.direction)
            self._starting_points.append(node.spawn_point)

        self._is_running = False                    # flag indicating if the simulation is running or not
        self._function_names = function_names       # list of function names to be invoked by the nodes
        self._named_functions = named_functions     # a dict of function definitions to be invoked
        self._chunk_size = 8192

        self._simulation_bus = SimulationBus(packetencoder=SimpleStringEncoder())

        self._stationary_node_name_prefix = Name("/rsu")
        self._mobile_node_to_computation = [0, 0, 0, 0, 0]  # index which mobile node issues which computation
        if use_distribution_helper:
            # TODO in the future support more distribution types, e.g., uniform, gaussian, etc.
            dist_array = ZipfMandelbrotDistribution.create_zipf_mandelbrot_distribution(
                len(self._function_names), 0.7, 0.7)
            for i in range(0, len(mobile_nodes)):
                self._mobile_node_to_computation[i] = ZipfMandelbrotDistribution.\
                    get_next_zipfmandelbrot_random_number(dist_array, len(self._function_names)) - 1

        self._compute_rsu_connection_time()
        self._setup_simulation_network()

    ###########################
    # METHODS
    ###########################

    def _compute_rsu_connection_time(self):
        """this method computes the connection time of a mobile node to a stationary node based on velocity of the mobile
        node and the communication range of the stationary node. Further enhancements of this simulation should include
        physical and MAC layer related communication conditions (e.g., propagation delay, fading, etc.) """

        self._contact_time = []
        for mobile_node in self._mobile_nodes:
            speed_in_ms = mobile_node.speed/3.6
            distance_in_m = 1000 * self._stationary_node_distance
            self._contact_time.append(distance_in_m / speed_in_ms * 1e9)

    def _setup_stationary_nodes(self):
        """configure the NFN com. stack at the stationary nodes"""

        for node in self._stationary_nodes:
            # install the NFN forwarder and the mgmt client tool at the stationary node
            if self._forwarder == "NFNForwarder":
                node.nfn_forwarder = NFNForwarder(0, encoder=SimpleStringEncoder(),
                                                  interfaces=[self._simulation_bus.add_interface(f"rsu{node.node_id}")],
                                                  ageing_interval=10)
            elif self._forwarder == "NFNForwarderData":
                node.nfn_forwarder = NFNForwarderData(0, encoder=SimpleStringEncoder(),
                                                      interfaces=[self._simulation_bus.add_interface(f"rsu{node.node_id}")],
                                                      chunk_size=self._chunk_size, num_of_forwards=1, ageing_interval=10)
            else:
                print("Forwarder: " + self._forwarder + " is not supported! Use 'NFNForwarder' or 'NFNForwarderData'!")

            # install the optimizer
            if self._optimizer == "ToDataFirstOptimizer":
                node.nfn_forwarder.nfnlayer.optimizer = ToDataFirstOptimizer(node.nfn_forwarder.icnlayer.cs,
                                                                             node.nfn_forwarder.icnlayer.fib,
                                                                             node.nfn_forwarder.icnlayer.pit,
                                                                             node.nfn_forwarder.linklayer.faceidtable)
            elif self._optimizer == "EdgeComputingOptimizer":
                node.nfn_forwarder.nfnlayer.optimizer = EdgeComputingOptimizer(node.nfn_forwarder.icnlayer.cs,
                                                                               node.nfn_forwarder.icnlayer.fib,
                                                                               node.nfn_forwarder.icnlayer.pit,
                                                                               node.nfn_forwarder.linklayer.faceidtable)
            # install the mgmt client tool at the node
            node.mgmt_tool = MgmtClient(node.nfn_forwarder.mgmt.mgmt_sock.getsockname()[1])
            node.nfn_forwarder.icnlayer.cs.set_cs_timeout(60)

    def _setup_connections_for_stationary_nodes(self):
        """configure the connections """

        loop_variable = 0
        for node in self._stationary_nodes:
            if loop_variable == 0:
                # setup first RSU
                faceid_rsu_1st = node.nfn_forwarder.linklayer.faceidtable.get_or_create_faceid(AddressInfo("rsu" + str(1), 0))
                node.nfn_forwarder.icnlayer.fib.add_fib_entry(Name("/nR"), [faceid_rsu_1st])
            elif loop_variable == (len(self._stationary_nodes) - 1):
                # setup last RSU
                faceid_rsu_last = node.nfn_forwarder.linklayer.faceidtable.get_or_create_faceid(
                    AddressInfo("rsu" + str(loop_variable - 2), 0))
                node.nfn_forwarder.icnlayer.fib.add_fib_entry(Name("/nL"), [faceid_rsu_last])
            else:
                faceid_node_left = node.nfn_forwarder.linklayer.faceidtable.get_or_create_faceid(
                    AddressInfo("rsu" + str(loop_variable - 1), 0))
                faceid_node_right = node.nfn_forwarder.linklayer.faceidtable.get_or_create_faceid(
                    AddressInfo("rsu" + str(loop_variable + 1), 0))

                node.nfn_forwarder.icnlayer.fib.add_fib_entry(Name("/nL"), [faceid_node_left])
                node.nfn_forwarder.icnlayer.fib.add_fib_entry(Name("/nR"), [faceid_node_right])
            loop_variable =+ 1

    def _assign_named_functions_to_stationary_execution_nodes(self):
        """configure executables to the stationary nodes"""

        for node in self._stationary_nodes:
            for function in zip(self._named_functions.keys(), self._named_functions.values()):
                node.nfn_forwarder.icnlayer.cs.add_content_object(Content(Name(function[0]), function[1]), static=True)

    def _setup_mobile_nodes(self):
        """configure the mobile nodes"""

        for node in self._mobile_nodes:
            node.forwarder = ICNForwarder(0, encoder=SimpleStringEncoder(), routing=True,
                                          interfaces=[self._simulation_bus.add_interface(f"car{node.node_id}")])
            node.fetch = Fetch(f"car{node.node_id}", None, 255, SimpleStringEncoder(),
                                        interfaces=[self._simulation_bus.add_interface(f"ftcar{node.node_id}")])
            node.mgmt_tool = MgmtClient(node.forwarder.mgmt.mgmt_sock.getsockname()[1])

            for stationary_node in self._stationary_nodes:
                car_face_id = node.forwarder.linklayer.faceidtable.get_or_create_faceid(
                    AddressInfo(f"rsu{stationary_node.node_id}", 0))
                self.to_rsu_faces[stationary_node.node_id][node.node_id] = car_face_id

                rsu_face_id = node.forwarder.linklayer.faceidtable.get_or_create_faceid(
                    AddressInfo(f"car{stationary_node.node_id}", 0))
                self.to_car_faces[stationary_node.node_id][node.node_id] = rsu_face_id

    def _setup_simulation_network(self):
        """configure a network according to the configuration"""

        self.logger.debug("Setup simulation network ...")
        # setup stationary nodes
        self._setup_stationary_nodes()
        self.logger.debug("\t setup stationary nodes done")

        # setup connections
        self._setup_connections_for_stationary_nodes()
        self.logger.debug("\t setup connections between stationary nodes done")

        # assign functions to stationary nodes
        self._assign_named_functions_to_stationary_execution_nodes()
        self.logger.debug("\t assign named functions to stationary nodes done")

        # setup mobile nodes
        self._setup_mobile_nodes()
        self.logger.debug("\t setup mobile nodes done")

        # start node
        self.start_nodes()
        self.logger.debug("\t setup complete -> start nodes")

    def reconnect_car(self, mobile_node_number, new_rsu_number):

        if len(self._stationary_nodes) <= new_rsu_number or new_rsu_number < 0:
            print(f"{time.time():.5f} --- Cannot reconnect mobile node with id {mobile_node_number} "
                  f"to stationary node with id {new_rsu_number}, not part of this simulation")
            return

        connected_rsu = self.connected_rsu[mobile_node_number]
        self._mobile_nodes[mobile_node_number].forwarder.icnlayer.fib.remove_fib_entry(self._stationary_node_name_prefix)
        self._mobile_nodes[mobile_node_number].forwarder.icnlayer.fib.add_fib_entry(self._stationary_node_name_prefix,
                                                                   [self.to_rsu_faces[new_rsu_number][mobile_node_number]])
        self._stationary_nodes[connected_rsu].nfn_forwarder.icnlayer.fib.remove_fib_entry(
            Name(f"/car/car{mobile_node_number}"))

        self._stationary_nodes[connected_rsu].nfn_forwarder.icnlayer.pit.remove_pit_entry_by_fid(
            self.to_car_faces[connected_rsu][mobile_node_number])

        self._stationary_nodes[new_rsu_number].nfn_forwarder.icnlayer.fib.add_fib_entry(
            Name(f"/car/car{mobile_node_number}"), [self.to_car_faces[new_rsu_number][mobile_node_number]])
        self.connected_rsu[mobile_node_number] = self.connected_rsu[connected_rsu] + \
                                                 self._heading_directions[connected_rsu]

        self._car_send_interest(self._mobile_nodes[mobile_node_number],
                                self._function_names[self._mobile_node_to_computation[mobile_node_number]])

    def _car_send_interest(self, mobile_node, name):
        try:
            mobile_node.fetch.fetch_data(name, timeout=1) # if trouble reduce timeout to 0.1. Parse result from log
        except:
            pass

    def start_nodes(self):
        # Starting nodes
        for stationary_node in self._stationary_nodes:
            stationary_node.nfn_forwarder.start_forwarder()
        for mobile_node in self._mobile_nodes:
            mobile_node.forwarder.start_forwarder()
        self._simulation_bus.start_process()

    def stop_nodes(self):
        # stop nodes
        if not self._is_running:
            for stationary_node in self._stationary_nodes:
                stationary_node.nfn_forwarder.stop_forwarder()
            for mobile_node in self._mobile_nodes:
                mobile_node.forwarder.stop_forwarder()
            self._simulation_bus.stop_process()
        else:
            print("Simulation not started yet -- cleaning resources is unnecessary!")

    def run(self):
        """run the experiment, hand over the cars"""
        self._is_running = True
        self.connected_rsu = []

        self.logger.debug("Start Simulation")

        for i in range(0, len(self._mobile_nodes)):
            self.connected_rsu.append(self._starting_points[i])
            self._mobile_nodes[i].forwarder.icnlayer.fib.add_fib_entry(self._stationary_node_name_prefix,
                                                             [self.to_rsu_faces[self.connected_rsu[i]][i]])
            self._stationary_nodes[self.connected_rsu[i]].nfn_forwarder.icnlayer.fib.add_fib_entry(Name(f"car{i}"),
                                                                        [self.to_car_faces[self.connected_rsu[i]][i]])
            self._car_send_interest(self._mobile_nodes[i], self._function_names[self._mobile_node_to_computation[i]])

        self.connection_time = [time.time()] * len(self._mobile_nodes)

        steps = 5 * len(self._mobile_nodes)
        print(steps)
        while(self._is_running):
            time_ns = time.time_ns()
            for i in range(0, len(self._mobile_nodes)):

                if time_ns - self.connection_time[i] > self._contact_time[i]:
                    print(f"{time.time():.5f} -- " + "Car", i, "reconnects from", self.connected_rsu[i], "to", self.connected_rsu[i] + self._heading_directions[i])
                    new_rsu_number = self.connected_rsu[i] + self._heading_directions[i]
                    self.reconnect_car(i, new_rsu_number)
                    self.connection_time[i] = time.time_ns()
                steps -=1

            if steps <= 0:
                self._is_running = False

        self.logger.debug("Simulation Terminated!")
        self.stop_nodes()
