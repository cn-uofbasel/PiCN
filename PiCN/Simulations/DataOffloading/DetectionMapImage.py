import ast
import base64
import unittest
from time import sleep
import os

from PiCN.Demos.DetectionMap.Helper import Helper
from PiCN.definitions import ROOT_DIR
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

#Dependencies for this test: numpy, matplotlib, cv2, requests, zipfile, tensorflow, pygeodesy
#Requires enabeling import in PiCN/Layers/NFNLayer/NFNExecutor/NFNPythonExecutor (See comments there, 3 lines)
class DetectionMapSimulation():
    """Run a simple Data Offloading Scenario Simulation"""

    def setUp(self):
        self.encoder_type = SimpleStringEncoder()
        self.simulation_bus = SimulationBus(packetencoder=self.encoder_type)
        chunk_size = 8192
        self.chunkifyer = SimpleContentChunkifyer(chunk_size)

        # Initialize two cars
        self.cars = []
        self.fetch_tool_cars = []
        self.mgmt_client_cars = []
        for i in range(2):
            self.cars.append(ICNForwarder(0, encoder=self.encoder_type, routing=True,
                                interfaces=[self.simulation_bus.add_interface(f"car{i}")]))
            self.fetch_tool_cars.append(Fetch(f"car{i}", None, 255, self.encoder_type,
                                    interfaces=[self.simulation_bus.add_interface(f"ftcar{i}")]))
            self.mgmt_client_cars.append(MgmtClient(self.cars[i].mgmt.mgmt_sock.getsockname()[1]))
            self.cars[i].icnlayer.cs.set_cs_timeout(40)

        # Initialize RSUs
        self.rsus = []
        self.fetch_tools = []
        self.mgmt_clients = []
        for i in range(3):
            self.rsus.append(NFNForwarderData(0, encoder=self.encoder_type,
                                              interfaces=[self.simulation_bus.add_interface(f"rsu{i}")],
                                              chunk_size=chunk_size, num_of_forwards=1, ageing_interval=10))
            self.fetch_tools.append(Fetch(f"rsu{i}", None, 255, self.encoder_type,
                                          interfaces=[self.simulation_bus.add_interface(f"ft{i}")]))
            self.rsus[i].nfnlayer.optimizer = EdgeComputingOptimizer(self.rsus[i].icnlayer.cs,
                                                                     self.rsus[i].icnlayer.fib,
                                                                     self.rsus[i].icnlayer.pit,
                                                                     self.rsus[i].linklayer.faceidtable)
            self.mgmt_clients.append(MgmtClient(self.rsus[i].mgmt.mgmt_sock.getsockname()[1]))
            self.fetch_tools[i].timeoutpreventionlayer.timeout_interval = 40
            self.rsus[i].icnlayer.cs.set_cs_timeout(60)

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

        function1 = "PYTHON\nf\ndef f(a, b, c):\n return detection_map(a, b, c)"
        function2 = "PYTHON\nf\ndef f(a, b, c):\n return detection_map_2(a, b, c)"

        # Setup rsu0
        self.mgmt_clients[0].add_face("car0", None, 0)
        self.mgmt_clients[0].add_face("car1", None, 0)
        self.mgmt_clients[0].add_face("rsu1", None, 0)
        self.mgmt_clients[0].add_forwarding_rule(Name("/car0"), [0])
        self.mgmt_clients[0].add_forwarding_rule(Name("/car1"), [1])
        self.mgmt_clients[0].add_forwarding_rule(Name("/nR"), [2])
        self.mgmt_clients[0].add_new_content(Name("/rsu/func/f1"), function1)
        self.mgmt_clients[0].add_new_content(Name("/rsu/func/f2"), function2)

        # Setup rsu1
        self.mgmt_clients[1].add_face("car0", None, 0)
        self.mgmt_clients[1].add_face("car1", None, 0)
        self.mgmt_clients[1].add_face("rsu0", None, 0)
        self.mgmt_clients[1].add_face("rsu2", None, 0)
        self.mgmt_clients[1].add_forwarding_rule(Name("/car0"), [0])
        self.mgmt_clients[1].add_forwarding_rule(Name("/car1"), [1])
        self.mgmt_clients[1].add_forwarding_rule(Name("/nL"), [2])
        self.mgmt_clients[1].add_forwarding_rule(Name("/nR"), [3])
        self.mgmt_clients[1].add_new_content(Name("/rsu/func/f1"), function1)
        self.mgmt_clients[1].add_new_content(Name("/rsu/func/f2"), function2)

        # Setup rsu2
        self.mgmt_clients[2].add_face("car0", None, 0)
        self.mgmt_clients[2].add_face("car1", None, 0)
        self.mgmt_clients[2].add_face("rsu1", None, 0)
        self.mgmt_clients[2].add_forwarding_rule(Name("/car0"), [0])
        self.mgmt_clients[2].add_forwarding_rule(Name("/car1"), [1])
        self.mgmt_clients[2].add_forwarding_rule(Name("/nL"), [2])

        # Setup car0
        self.mgmt_client_cars[0].add_face("rsu0", None, 0)
        self.mgmt_client_cars[0].add_face("rsu1", None, 0)
        self.mgmt_client_cars[0].add_face("rsu2", None, 0)
        self.mgmt_client_cars[0].add_forwarding_rule(Name("/rsu"), [0])

        # Setup car1
        self.mgmt_client_cars[1].add_face("rsu0", None, 0)
        self.mgmt_client_cars[1].add_face("rsu1", None, 0)
        self.mgmt_client_cars[1].add_face("rsu2", None, 0)
        self.mgmt_client_cars[1].add_forwarding_rule(Name("/rsu"), [0])

        # Add image to content store of car0
        # Streetview 1
        # image_path = os.path.join(ROOT_DIR, "Demos/DetectionMap/Assets/street1.jpg")
        # image_path = os.path.join(ROOT_DIR, "Demos/DetectionMap/Assets/image1_small.jpg")
        image_path = os.path.join(ROOT_DIR, "Demos/DetectionMap/Assets/image8.jpg")
        base64_image = Helper.pre_process(image_path, 2048, 2, ".jpg")
        # map_det_obj0 = DetectionMapObject(base64_image, 47.566192, 7.590686, 65, 0.4, 1.8)
        # map_det_obj0 = DetectionMapObject(base64_image, 47.377391, 8.539347, 294, 0.8)
        map_det_obj0 = DetectionMapObject(base64_image, 47.369645, 8.539652, 300, 0.7, 0.8)
        image = Content(Name("/car0/image"), map_det_obj0.to_string())
        self.meta_data0, self.data0 = self.chunkifyer.chunk_data(image)

        for md in self.meta_data0:
            self.cars[0].icnlayer.cs.add_content_object(md)

        for d in self.data0[:10]:
            self.cars[0].icnlayer.cs.add_content_object(d)

        # Add image to content store of car1
        # Streetview 2
        image_path = os.path.join(ROOT_DIR, "Demos/DetectionMap/Assets/street2.jpg")
        base64_image = Helper.pre_process(image_path, 1024, 2, ".jpg")
        map_det_obj1 = DetectionMapObject(base64_image, 47.566463, 7.590982, 345, 0.4, 1.8)
        image = Content(Name("/car1/image"), map_det_obj1.to_string())
        self.meta_data1, self.data1 = self.chunkifyer.chunk_data(image)

        for md in self.meta_data1:
            self.cars[1].icnlayer.cs.add_content_object(md)

        for d in self.data1:
            self.cars[1].icnlayer.cs.add_content_object(d)

    def test_map_detection_1_image(self):
        self.setup_faces_and_connections()

        name = Name("/rsu/func/f1")
        name += "_(/car0/image,1,0)"
        name += "NFN"

        print("RSU 0 FETCHING")
        result = self.fetch_tools[0].fetch_data(name, 360)
        print(result)

        sleep(2)
        print("\n" * 20 + "RSU 1 FETCHING")

        for d in self.data0[10:]:
            self.cars[0].icnlayer.cs.add_content_object(d)
        for d in self.data0[:10]:
            self.cars[0].icnlayer.cs.remove_content_object(d.name)
        # for md in self.meta_data0:
        #     self.cars[0].icnlayer.cs.remove_content_object(md.name)
        # for md in self.meta_data0:
        #     self.cars[0].icnlayer.cs.add_content_object(md)

        result = self.fetch_tools[1].fetch_data(name, 60)
        print(result)

        # result = list(ast.literal_eval(result))
        #
        # self.assertEqual(5, result[0][0])
        # self.assertEqual(2, result[1][0])
        # self.assertEqual(2, result[2][0])
        # self.assertEqual(1, result[3][0])
        # self.assertEqual(0, result[4][0])


    # def test_map_detection_2_images(self):
    #     self.setup_faces_and_connections()
    #
    #     name = Name("/rsu/func/f2")
    #     name += "_(/car0/image,/car1/image,1)"
    #     name += "NFN"
    #
    #     print("RSU 0 FETCHING")
    #     result = self.fetch_tools[0].fetch_data(name, 60)
    #     print(result)
    #
    #     sleep(2)
    #     print("\n" * 20 + "RSU 1 FETCHING")
    #
    #     for d in self.data0[10:]:
    #         self.cars[0].icnlayer.cs.add_content_object(d)
    #     for d in self.data0[:10]:
    #         self.cars[0].icnlayer.cs.remove_content_object(d.name)
    #     # for md in self.meta_data0[3:]:
    #     #     self.cars[0].icnlayer.cs.add_content_object(md)
    #
    #     for d in self.data1:
    #         self.cars[1].icnlayer.cs.remove_content_object(d.name)
    #     for md in self.meta_data1:
    #         self.cars[1].icnlayer.cs.remove_content_object(md.name)
    #
    #     res2 = self.fetch_tools[1].fetch_data(name, 60)
    #     print(res2)