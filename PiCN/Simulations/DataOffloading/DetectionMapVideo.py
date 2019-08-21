import base64
import unittest
import cv2
import os
import json
import numpy as np
from time import sleep, time

from PiCN.definitions import ROOT_DIR
from PiCN.Demos.DetectionMap.DetectionMap import detection_map
from PiCN.Layers.ChunkLayer.Chunkifyer import SimpleContentChunkifyer
from PiCN.Layers.LinkLayer.Interfaces import SimulationBus
from PiCN.Layers.NFNLayer.NFNOptimizer import EdgeComputingOptimizer
from PiCN.Layers.PacketEncodingLayer.Encoder import SimpleStringEncoder
from PiCN.Mgmt import MgmtClient
from PiCN.Packets import Name, Content
from PiCN.ProgramLibs.Fetch import Fetch
from PiCN.ProgramLibs.ICNForwarder import ICNForwarder
from PiCN.ProgramLibs.NFNForwarder.NFNForwarderData import NFNForwarderData
from PiCN.Demos.DetectionMap.DetectionMapObject import DetectionMapObject
from PiCN.Demos.DetectionMap.Helper import Helper


#Dependencies for this test: numpy, matplotlib, cv2, requests, zipfile, tensorflow, pygeodesy
#Requires enabeling import in PiCN/Layers/NFNLayer/NFNExecutor/NFNPythonExecutor (See comments there, 3 lines)
class DetectionMapVideoSimulation():
    """Run a simple data-offloading simulation"""

    def setUp(self):
        self.encoder_type = SimpleStringEncoder()
        self.simulation_bus = SimulationBus(packetencoder=self.encoder_type)
        chunk_size = 8192
        self.chunkifyer = SimpleContentChunkifyer(chunk_size)

        # initialize two cars
        self.cars = []
        self.fetch_tool_cars = []
        self.mgmt_client_cars = []
        for i in range(2):
            self.cars.append(ICNForwarder(0, encoder=self.encoder_type, routing=True,
                                interfaces=[self.simulation_bus.add_interface(f"car{i}")]))
            self.fetch_tool_cars.append(Fetch(f"car{i}", None, 255, self.encoder_type,
                                    interfaces=[self.simulation_bus.add_interface(f"ftcar{i}")]))
            self.mgmt_client_cars.append(MgmtClient(self.cars[i].mgmt.mgmt_sock.getsockname()[1]))
            self.cars[i].icnlayer.cs.set_cs_timeout(30)

        # initialize RSUs
        self.rsus = []
        self.fetch_tools = []
        self.mgmt_clients = []
        for i in range(3):
            self.rsus.append(NFNForwarderData(0, encoder=self.encoder_type,
                                              interfaces=[self.simulation_bus.add_interface(f"rsu{i}")],
                                              chunk_size=chunk_size, num_of_forwards=1))
            self.fetch_tools.append(Fetch(f"rsu{i}", None, 255, self.encoder_type,
                                          interfaces=[self.simulation_bus.add_interface(f"ft{i}")]))
            self.rsus[i].nfnlayer.optimizer = EdgeComputingOptimizer(self.rsus[i].icnlayer.cs,
                                                                     self.rsus[i].icnlayer.fib,
                                                                     self.rsus[i].icnlayer.pit,
                                                                     self.rsus[i].linklayer.faceidtable)
            self.mgmt_clients.append(MgmtClient(self.rsus[i].mgmt.mgmt_sock.getsockname()[1]))
            self.fetch_tools[i].timeoutpreventionlayer.timeout_interval = 30

    def tearDown(self):
        for car in self.cars:
            car.stop_forwarder()

        for fetch_tool_car in self.fetch_tool_cars:
            fetch_tool_car.stop_fetch()

        for rsu in self.rsus:
            rsu.stop_forwarder()

        for fetch_tool in self.fetch_tools:
            fetch_tool.stop_fetch()

        self.simulation_bus.stop_process()

    def setup_faces_and_connections(self):
        for car in self.cars:
            car.start_forwarder()

        for rsu in self.rsus:
            rsu.start_forwarder()

        self.simulation_bus.start_process()

        function = "PYTHON\nf\ndef f(a, b, c):\n return detection_map(a, b, c)"

        # setup rsu0
        self.mgmt_clients[0].add_face("car0", None, 0)
        self.mgmt_clients[0].add_face("car1", None, 0)
        self.mgmt_clients[0].add_face("rsu1", None, 0)
        self.mgmt_clients[0].add_forwarding_rule(Name("/car0"), [0])
        self.mgmt_clients[0].add_forwarding_rule(Name("/car1"), [1])
        self.mgmt_clients[0].add_forwarding_rule(Name("/nR"), [2])
        self.mgmt_clients[0].add_new_content(Name("/rsu/func/f1"), function)

        # setup rsu1
        self.mgmt_clients[1].add_face("car0", None, 0)
        self.mgmt_clients[1].add_face("car1", None, 0)
        self.mgmt_clients[1].add_face("rsu0", None, 0)
        self.mgmt_clients[1].add_face("rsu2", None, 0)
        self.mgmt_clients[1].add_forwarding_rule(Name("/car0"), [0])
        self.mgmt_clients[1].add_forwarding_rule(Name("/car1"), [1])
        self.mgmt_clients[1].add_forwarding_rule(Name("/nL"), [2])
        self.mgmt_clients[1].add_forwarding_rule(Name("/nR"), [3])
        self.mgmt_clients[1].add_new_content(Name("/rsu/func/f1"), function)

        # setup rsu2
        self.mgmt_clients[2].add_face("car0", None, 0)
        self.mgmt_clients[2].add_face("car1", None, 0)
        self.mgmt_clients[2].add_face("rsu1", None, 0)
        self.mgmt_clients[2].add_forwarding_rule(Name("/car0"), [0])
        self.mgmt_clients[2].add_forwarding_rule(Name("/car1"), [1])
        self.mgmt_clients[2].add_forwarding_rule(Name("/nL"), [2])

        # setup car0
        self.mgmt_client_cars[0].add_face("rsu0", None, 0)
        self.mgmt_client_cars[0].add_face("rsu1", None, 0)
        self.mgmt_client_cars[0].add_face("rsu2", None, 0)
        self.mgmt_client_cars[0].add_forwarding_rule(Name("/rsu"), [0])

        # extract frames from video
        fps, frames = Helper.video_to_frames(os.path.join(ROOT_DIR, "Demos/DetectionMap/Assets/108.mp4"))
        fps = int(np.round(fps))

        # read json file containing gps coords and bearing
        # file contains one entry per second
        with open(os.path.join(ROOT_DIR, "Demos/DetectionMap/Assets/locations.json")) as f:
            data = json.load(f)
            locations = data.get("locations")

        # duplicate last entry, needed for the interpolation in the next step
        locations.append(locations[-1])

        # interpolate between the values to create one entry per frame
        lats = []
        longs = []
        bearings = []
        for i in range(len(locations)-1):
            lat_current = locations[i].get("latitude")
            lat_next = locations[i+1].get("latitude")

            long_current = locations[i].get("longitude")
            long_next = locations[i+1].get("longitude")

            bearing_current = locations[i].get("course")
            bearing_next = locations[i+1].get("course")

            if np.abs(lat_next - lat_current) > 0:
                lats.append(np.arange(lat_current, lat_next, (lat_next - lat_current) / fps))
            else:
                lats.append([lat_current] * fps)
            if np.abs(long_next - long_current) > 0:
                longs.append(np.arange(long_current, long_next, (long_next - long_current) / fps))
            else:
                longs.append([long_current] * fps)
            if np.abs(bearing_next - bearing_current) > 0:
                bearings.append(np.arange(bearing_current, bearing_next, (bearing_next - bearing_current) / fps))
            else:
                bearings.append([bearing_current] * fps)

        # flatten all the lists
        lats = [item for sublist in lats for item in sublist]
        longs = [item for sublist in longs for item in sublist]
        bearings = [item for sublist in bearings for item in sublist]

        self.mdos = []
        for i, frame in enumerate(frames):
            encoded = cv2.imencode('.jpg', frame)[1].tostring()
            base64_image = base64.b64encode(encoded)
            map_det_obj0 = DetectionMapObject(base64_image, 0.8, lats[i], longs[i], bearings[i])
            self.mdos.append(map_det_obj0)

    def test_detection_map_video(self):
        self.setup_faces_and_connections()
        n = 0
        for i, mdo in enumerate(self.mdos[n:60]):
            name = Name("/rsu/func/f1")
            name += f"_(/car0/image{i+n},1,{i+n})"
            name += "NFN"

            image = Content(Name(f"/car0/image{i+n}"), mdo.to_string())
            self.meta_data, self.data = self.chunkifyer.chunk_data(image)
            for md in self.meta_data:
                self.cars[0].icnlayer.cs.add_content_object(md)
            for d in self.data:
                self.cars[0].icnlayer.cs.add_content_object(d)

            print("\t" * 5)
            print("RSU 0 FETCHING")
            result = self.fetch_tools[0].fetch_data(name, 360)
            print(result)
            sleep(1)

        # create video file from the resulting plots and detections
        print("Creating video files...")
        path_in = os.path.join(ROOT_DIR, "Demos/DetectionMap/Assets/Plots/")
        path_out = os.path.join(ROOT_DIR, "Demos/DetectionMap/Assets/Videos/plots_video.mp4")
        Helper.frames_to_video(path_in, path_out, 30)

        path_in = os.path.join(ROOT_DIR, "Demos/DetectionMap/Assets/Classified/")
        path_out = os.path.join(ROOT_DIR, "Demos/DetectionMap/Assets/Videos/detections_video.mp4")
        Helper.frames_to_video(path_in, path_out, 30)
