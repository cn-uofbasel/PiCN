"""Parametrized Mobile Edge Computing Simulation to test cars driving with a certain speed trough a network"""


import ast
import base64
import unittest
from time import sleep
import os
import time
import random

from PiCN.Demos.DetectionMap.Helper import Helper
from PiCN.definitions import ROOT_DIR
from PiCN.Layers.ChunkLayer.Chunkifyer import SimpleContentChunkifyer
from PiCN.Layers.LinkLayer.Interfaces import SimulationBus
from PiCN.Layers.NFNLayer.NFNOptimizer import EdgeComputingOptimizer
from PiCN.Layers.PacketEncodingLayer.Encoder import SimpleStringEncoder
from PiCN.Mgmt import MgmtClient
from PiCN.Packets import Name, Content, Interest
from PiCN.ProgramLibs.Fetch import Fetch
from PiCN.ProgramLibs.ICNForwarder import ICNForwarder
from PiCN.ProgramLibs.NFNForwarder.NFNForwarderData import NFNForwarderData
from PiCN.Demos.DetectionMap.DetectionMapObject import DetectionMapObject
from PiCN.Layers.LinkLayer.Interfaces import AddressInfo


class MobileEdgeComputingSimulation():
    """Mobile Edge Computing Simulation"""


    def __init__(self):
        """define the configuration"""
        self.number_of_rsus = 4
        self.number_of_cars = 5
        self.to_car_faces = [[0] * self.number_of_cars for i in range(self.number_of_rsus)] #rsu, car -> faceid
        self.to_rsu_faces = [[0] * self.number_of_cars for i in range(self.number_of_rsus)] #rsu, car -> faceid
        self.car_speed = [60, 60, 60, 60, 60] #in km/h
        self.car_direction = [1, 1 ,1 ,1 ,1] # 1 or -1, consider starting rsu by choosing direction.

        self.starting_rsu = [0, 0, 0, 0, 0]

        self.rsu_distance = 0.5 #in km, range is identical here

        self.computations = self.get_computations() #Store computations in here, car will randomly choose one
        self.named_functions ={"/rsu/func/f1": "PYTHON\nf\ndef f(a, b, c):\n return a+b+c",
                             "/rsu/func/f2": "PYTHON\nf\ndef f(a, b, c):\n return a*b*c"} #named functions stored on the
        self.chunk_size = 8192

        self.optimizer = EdgeComputingOptimizer #NFN resolution strategy optimizer
        self.encoder_type = SimpleStringEncoder()
        self.simulation_bus = SimulationBus(packetencoder=self.encoder_type)

        self.rsu_name = Name("/rsu")

        self.car_to_computation = [0,0,0,0,0] #index which car issues which computation

        self._compute_rsu_connection_time()
        self.setup_network()


    def get_computations(self):
        comps = []
        c1 = Name("/rsu/func/f1")
        c1 += "_(1,2,3)"
        c1 += "NFN"
        comps.append(c1)

        return comps




    def _compute_rsu_connection_time(self):
        """compute the connection time based on speed and distance"""

        self.contact_time = []
        for s in self.car_speed:
            speed_in_ms = s/3.6
            distance_in_m = 1000*self.rsu_distance
            self.contact_time.append(distance_in_m/speed_in_ms * 1e9)


    def setup_network(self):
        """configure a network according to the configuration"""

        #create RSUs and RSU mgmt tools
        self.rsus = []
        self.mgmt_rsu = []
        for i in range(0, self.number_of_rsus):


            rsu = NFNForwarderData(0, encoder=self.encoder_type,
                             interfaces=[self.simulation_bus.add_interface(f"rsu{i}")],
                             chunk_size=self.chunk_size, num_of_forwards=1, ageing_interval=10)
            rsu.nfnlayer.optimizer = self.optimizer(rsu.icnlayer.cs, rsu.icnlayer.fib, rsu.icnlayer.pit,
                                                    rsu.linklayer.faceidtable)
            mgmt_client = MgmtClient(rsu.mgmt.mgmt_sock.getsockname()[1])
            self.rsus.append(rsu)
            self.mgmt_rsu.append(mgmt_client)
            self.rsus[i].icnlayer.cs.set_cs_timeout(60)

        #setup connections
        for i in range(1, self.number_of_rsus-1):

            #setup connections between rsus
            faceid_rsu_l = self.rsus[i].linklayer.faceidtable.get_or_create_faceid(AddressInfo("rsu" + str(i-1), 0))
            faceid_rsu_r = self.rsus[i].linklayer.faceidtable.get_or_create_faceid(AddressInfo("rsu" + str(i+1), 0))

            self.rsus[i].icnlayer.fib.add_fib_entry(Name("/nL"), [faceid_rsu_l])
            self.rsus[i].icnlayer.fib.add_fib_entry(Name("/nR"), [faceid_rsu_r])


        #setup first and last rsu
        faceid_rsu_1st = self.rsus[0].linklayer.faceidtable.get_or_create_faceid(AddressInfo("rsu" + str(1), 0))
        faceid_rsu_last = self.rsus[self.number_of_rsus-1].linklayer.faceidtable.get_or_create_faceid(AddressInfo("rsu" + str(self.number_of_rsus-2), 0))

        self.rsus[0].icnlayer.fib.add_fib_entry(Name("/nR"), [faceid_rsu_1st])
        self.rsus[self.number_of_rsus-1].icnlayer.fib.add_fib_entry(Name("/nL"), [faceid_rsu_last])


        #add function
        for i in range(0, self.number_of_rsus):

            for n in zip(self.named_functions.keys(), self.named_functions.values()):
                add_msg = self.rsus[i].icnlayer.cs.add_content_object(Content(Name(n[0]), n[1]), static=True)

        #setup cars
        self.car_forwarders = []
        self.car_fetch = []
        self.car_mgmt = []
        for i in range (0, self.number_of_cars):
            self.car_forwarders.append(ICNForwarder(0, encoder=self.encoder_type, routing=True,
                                interfaces=[self.simulation_bus.add_interface(f"car{i}")]))
            self.car_fetch.append(Fetch(f"car{i}", None, 255, self.encoder_type,
                                    interfaces=[self.simulation_bus.add_interface(f"car{i}")]))
            mgmt_client_car = MgmtClient(self.car_forwarders[i].mgmt.mgmt_sock.getsockname()[1])
            self.car_mgmt.append(mgmt_client_car)

            for j in range(0, self.number_of_rsus):
                car_face_id = self.car_forwarders[i].linklayer.faceidtable.get_or_create_faceid(AddressInfo(f"rsu{j}", 0))
                self.to_rsu_faces[j][i] = car_face_id

                rsu_face_id = self.rsus[j].linklayer.faceidtable.get_or_create_faceid(AddressInfo(f"car{i}", 0))
                self.to_car_faces[j][i] = rsu_face_id

        #Starting nodes

        for i in range(0, self.number_of_rsus):
            self.rsus[i].start_forwarder()
        for i in range(0, self.number_of_cars):
            self.car_forwarders[i].start_forwarder()
        self.simulation_bus.start_process()



    def reconnect_car(self, car_number, new_rsu_number):

        if self.number_of_rsus <= new_rsu_number or new_rsu_number < 0:
            print(f"{time.time():.5f} --- Cannot Reconnect Car {car_number} to RSU {new_rsu_number}, not part of this simulation")
            return

        connected_rsu = self.connected_rsu[car_number]
        self.car_forwarders[car_number].icnlayer.fib.remove_fib_entry(self.rsu_name)
        self.car_forwarders[car_number].icnlayer.fib.add_fib_entry(self.rsu_name, [self.to_rsu_faces[new_rsu_number][car_number]])
        self.rsus[connected_rsu].icnlayer.fib.remove_fib_entry(Name(f"/car/car{car_number}"))

        self.rsus[connected_rsu].icnlayer.pit.remove_fib_entry_by_fid(self.to_car_faces[connected_rsu][car_number])

        self.rsus[new_rsu_number].icnlayer.fib.add_fib_entry(Name(f"/car/car{car_number}"), [self.to_car_faces[new_rsu_number][car_number]])
        self.connected_rsu[car_number] = self.connected_rsu[connected_rsu] + self.car_direction[connected_rsu]


        print(type(self.computations[self.car_to_computation[car_number]]))
        self.car_send_interest(car_number, self.computations[self.car_to_computation[car_number]])


    def car_send_interest(self, number, name):
        self.car_fetch[number].fetch_data(name, timeout=1) # if trouble reduce timeout to 0.1. Parse result from log


    def mainloop(self):
        """run the experiment, hand over the cars"""
        isRunning = True
        self.connected_rsu = []

        #connect cars to the initial RSU
        for i in range(0, self.number_of_cars):
            self.connected_rsu.append(self.starting_rsu[i])
            self.car_forwarders[i].icnlayer.fib.add_fib_entry(self.rsu_name, [self.to_rsu_faces[self.connected_rsu[i]][i]])
            self.rsus[self.connected_rsu[i]].icnlayer.fib.add_fib_entry(Name(f"car{i}"),
                                                                 [self.to_car_faces[self.connected_rsu[i]][i]])

        self.connection_time = [time.time_ns()] * self.number_of_cars
        steps = 3 * self.number_of_cars
        while(isRunning):
            time_ns = time.time_ns()
            for i in range(0, self.number_of_cars):

                if time_ns - self.connection_time[i] > self.contact_time[i]:
                    print(f"{time.time():.5f} ---" + " Car", i, "reconnects from", self.connected_rsu[i], "to", self.connected_rsu[i] + self.car_direction[i])
                    new_rsu_number = self.connected_rsu[i] + self.car_direction[i]
                    self.reconnect_car(i, new_rsu_number)
                    self.connection_time[i] = time.time_ns()
                    steps -=1

            if steps < 0:
                break

def main():
    sim = MobileEdgeComputingSimulation()
    print(f"{time.time():.5f} ---" + "Setup Finished, Running Simulation")
    sim.mainloop()


if __name__ == "__main__":
    main()













