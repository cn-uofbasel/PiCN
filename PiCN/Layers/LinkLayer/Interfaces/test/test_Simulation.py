"""Test the PiCN Simulation System"""

import abc
import queue
import unittest
import os

from PiCN.Layers.LinkLayer.Interfaces import SimulationBus
from PiCN.Layers.LinkLayer.Interfaces import AddressInfo
from PiCN.ProgramLibs.ICNForwarder import ICNForwarder
from PiCN.ProgramLibs.NFNForwarder import NFNForwarder
from PiCN.ProgramLibs.ICNDataRepository import ICNDataRepository
from PiCN.Layers.PacketEncodingLayer.Encoder import BasicEncoder, SimpleStringEncoder, NdnTlvEncoder
from PiCN.Packets import Content, Interest, Name
from PiCN.Mgmt import MgmtClient

class cases_Simulation():
    """Test the PiCN Simulation System"""

    @abc.abstractmethod
    def get_encoder(self) ->BasicEncoder:
        pass

    def setUp(self):
        self.encoder_type = self.get_encoder()

        self.simulation_bus = SimulationBus(packetencoder=self.encoder_type())

        self.fetchiface = self.simulation_bus.add_interface("fetch")
        self.encoder = self.encoder_type()
        self.icn_forwarder1 = ICNForwarder(port=0, encoder=self.encoder_type(),
                                           interfaces=[self.simulation_bus.add_interface("icnfwd1")], log_level=255)
        self.icn_forwarder2 = ICNForwarder(port=0, encoder=self.encoder_type(),
                                           interfaces=[self.simulation_bus.add_interface("icnfwd2")], log_level=255)

        #self.simulation_bus.start_process()

    def tearDown(self):
        try:
            self.simulation_bus.stop_process()
            self.icn_forwarder1.stop_forwarder()
            self.icn_forwarder2.stop_forwarder()
        except:
            self.icn_forwarder2.stop_repo()
            pass

    def test_send_single_packet(self):
        """Test fetching a single content object over the simulation bus"""
        self.icn_forwarder1.start_forwarder()
        self.icn_forwarder2.start_forwarder()
        self.simulation_bus.start_process()

        fid1 = self.icn_forwarder1.linklayer.faceidtable.get_or_create_faceid(AddressInfo("icnfwd2", 0))
        self.icn_forwarder1.icnlayer.fib.add_fib_entry(Name("/test"), fid1)

        self.icn_forwarder2.icnlayer.cs.add_content_object(Content("/test/data", "HelloWorld"), static=True)

        interest = Interest("/test/data")
        wire_data = self.encoder.encode(interest)
        self.fetchiface.send(wire_data, "icnfwd1")

        res, src = self.fetchiface.receive()
        self.assertEqual(src, "icnfwd1")
        c = self.encoder.decode(res)
        self.assertEqual(c, Content("/test/data", "HelloWorld"))

    def test_send_single_packet_with_delay(self):
        """Test fetching a single content object over the simulation bus"""

        delay_func = lambda packet: 0.5

        self.fetchiface = self.simulation_bus.add_interface("fetch", delay_func=delay_func)
        self.icn_forwarder1 = ICNForwarder(port=0, encoder=self.encoder_type(),
                                           interfaces=[self.simulation_bus.add_interface("icnfwd1", delay_func=delay_func)])
        self.icn_forwarder2 = ICNForwarder(port=0, encoder=self.encoder_type(),
                                           interfaces=[self.simulation_bus.add_interface("icnfwd2", delay_func=delay_func)])
        self.simulation_bus.start_process()

        self.icn_forwarder1.start_forwarder()
        self.icn_forwarder2.start_forwarder()

        fid1 = self.icn_forwarder1.linklayer.faceidtable.get_or_create_faceid(AddressInfo("icnfwd2", 0))
        self.icn_forwarder1.icnlayer.fib.add_fib_entry(Name("/test"), fid1)

        self.icn_forwarder2.icnlayer.cs.add_content_object(Content("/test/data", "HelloWorld"), static=True)

        interest = Interest("/test/data")
        wire_data = self.encoder.encode(interest)
        self.fetchiface.send(wire_data, "icnfwd1")

        res, src = self.fetchiface.receive()
        self.assertEqual(src, "icnfwd1")
        c = self.encoder.decode(res)
        self.assertEqual(c, Content("/test/data", "HelloWorld"))

    def test_send_single_packet_with_packet_loss(self):
        """Test fetching a single content object over the simulation bus"""

        packet_loss_func = lambda packet: True

        self.fetchiface = self.simulation_bus.add_interface("fetch", packet_loss_func=packet_loss_func)
        self.icn_forwarder1 = ICNForwarder(port=0, encoder=self.encoder_type(),
                                           interfaces=[self.simulation_bus.add_interface("icnfwd1", packet_loss_func=packet_loss_func)])
        self.icn_forwarder2 = ICNForwarder(port=0, encoder=self.encoder_type(),
                                           interfaces=[self.simulation_bus.add_interface("icnfwd2", packet_loss_func=packet_loss_func)])
        self.simulation_bus.start_process()

        self.icn_forwarder1.start_forwarder()
        self.icn_forwarder2.start_forwarder()

        fid1 = self.icn_forwarder1.linklayer.faceidtable.get_or_create_faceid(AddressInfo("icnfwd2", 0))
        self.icn_forwarder1.icnlayer.fib.add_fib_entry(Name("/test"), fid1)

        self.icn_forwarder2.icnlayer.cs.add_content_object(Content("/test/data", "HelloWorld"), static=True)

        interest = Interest("/test/data")
        wire_data = self.encoder.encode(interest)
        self.fetchiface.send(wire_data, "icnfwd1")
        try:
            self.fetchiface.receive(timeout=4)
        except queue.Empty:
            pass
        else:
            self.fail()

    def test_creation_of_simulation_face_mgmt(self):
        """Test the creation of a simulation face using a mgmt client"""
        self.icn_forwarder1.start_forwarder()
        self.icn_forwarder2.start_forwarder()

        self.simulation_bus.start_process()

        mgmt_client1 = MgmtClient(self.icn_forwarder1.mgmt.mgmt_sock.getsockname()[1])

        mgmt_client1.add_face("icnfwd2", None, 0)
        mgmt_client1.add_forwarding_rule(Name("/test"), 0)

        mgmt_client2 = MgmtClient(self.icn_forwarder2.mgmt.mgmt_sock.getsockname()[1])
        mgmt_client2.add_new_content(Name("/test/data"), "HelloWorld")

        interest = Interest("/test/data")
        wire_data = self.encoder.encode(interest)
        self.fetchiface.send(wire_data, "icnfwd1")

        res, src = self.fetchiface.receive()
        self.assertEqual(src, "icnfwd1")
        c = self.encoder.decode(res)
        self.assertEqual(c, Content("/test/data", "HelloWorld"))

        mgmt_client1.shutdown()
        mgmt_client2.shutdown()


    def test_bandwidth_limit(self): #TODO better test here
        """Simple Test for checking the bandwidth limit"""

        self.icn_forwarder1.start_forwarder()
        self.icn_forwarder2.start_forwarder()

        self.simulation_bus.start_process()

        mgmt_client1 = MgmtClient(self.icn_forwarder1.mgmt.mgmt_sock.getsockname()[1])

        mgmt_client1.add_face("icnfwd2", None, 0)
        mgmt_client1.add_forwarding_rule(Name("/test"), 0)

        mgmt_client2 = MgmtClient(self.icn_forwarder2.mgmt.mgmt_sock.getsockname()[1])
        mgmt_client2.add_new_content(Name("/test/data"), "HelloWorld")

        interest = Interest("/test/data")
        wire_data = self.encoder.encode(interest)
        self.fetchiface.send(wire_data, "icnfwd1")

        res, src = self.fetchiface.receive()
        self.assertEqual(src, "icnfwd1")
        c = self.encoder.decode(res)
        self.assertEqual(c, Content("/test/data", "HelloWorld"))

        mgmt_client1.shutdown()
        mgmt_client2.shutdown()

    def test_single_nfn_interest(self):
        """Test simulation with NFN nodes and a single packet """

        self.icn_forwarder1 = NFNForwarder(port=0, encoder=self.encoder_type(),
                                           interfaces=[self.simulation_bus.add_interface("icnfwd1")])
        self.icn_forwarder2 = NFNForwarder(port=0, encoder=self.encoder_type(),
                                           interfaces=[self.simulation_bus.add_interface("icnfwd2")])
        self.icn_forwarder1.start_forwarder()
        self.icn_forwarder2.start_forwarder()
        self.simulation_bus.start_process()

        mgmt_client1 = MgmtClient(self.icn_forwarder1.mgmt.mgmt_sock.getsockname()[1])
        mgmt_client1.add_face("icnfwd2", None, 0)
        mgmt_client1.add_forwarding_rule(Name("/test"), 0)
        mgmt_client1.add_new_content(Name("/func/f1"), "PYTHON\nf\ndef f(a):\n    return a.upper()")

        mgmt_client2 = MgmtClient(self.icn_forwarder2.mgmt.mgmt_sock.getsockname()[1])
        mgmt_client2.add_new_content(Name("/test/data"), "HelloWorld")
        mgmt_client2.add_face("icnfwd1", None, 0)
        mgmt_client2.add_forwarding_rule(Name("/func"), 0)

        interest = Interest("/test/data")
        interest.name += "/func/f1(_)"
        interest.name += "NFN"
        wire_data = self.encoder.encode(interest)

        self.fetchiface.send(wire_data, "icnfwd1")

        res, src = self.fetchiface.receive()
        self.assertEqual(src, "icnfwd1")
        c = self.encoder.decode(res)
        self.assertEqual(c, Content(interest.name, "HELLOWORLD"))

        mgmt_client1.shutdown()
        mgmt_client2.shutdown()

    def test_singl_interest_repo(self):
        """Test simulation by requesting data from a repo"""
        self.path = "/tmp/repo_unit_test"
        try:
            os.stat( self.path)
        except:
            os.mkdir( self.path)
        with open( self.path + "/f1", 'w+') as content_file:
            content_file.write("A"*20000)
        self.icn_forwarder2 = ICNDataRepository(self.path, Name("/test/data"), 0, log_level=255, encoder=self.encoder_type(),
                                                interfaces=[self.simulation_bus.add_interface("icnfwd2")])


        self.icn_forwarder1.start_forwarder()
        self.icn_forwarder2.start_repo()
        self.simulation_bus.start_process()

        mgmt_client1 = MgmtClient(self.icn_forwarder1.mgmt.mgmt_sock.getsockname()[1])
        mgmt_client1.add_face("icnfwd2", None, 0)
        mgmt_client1.add_forwarding_rule(Name("/test"), 0)

        interest = Interest("/test/data/f1")
        wire_data = self.encoder.encode(interest)

        self.fetchiface.send(wire_data, "icnfwd1")
        res, src = self.fetchiface.receive()
        self.assertEqual(src, "icnfwd1")
        c = self.encoder.decode(res)
        self.assertEqual(c, Content(interest.name, "mdo:/test/data/f1/c0;/test/data/f1/c1;/test/data/f1/c2;/test/data/f1/c3:/test/data/f1/m1"))

        mgmt_client1.shutdown()


class test_Simulation_Simple_Packet_Encoder(cases_Simulation, unittest.TestCase):
    """Test the PiCN Simulation System with the Simple Packet Encoder"""

    def get_encoder(self):
        return SimpleStringEncoder

class test_Simulation_NDNTLV_Packet_Encoder(cases_Simulation, unittest.TestCase):
    """Test the PiCN Simulation System with the NDNTLV Packet Encoder"""

    def get_encoder(self):
        return NdnTlvEncoder
