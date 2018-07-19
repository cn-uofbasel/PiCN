"""Test the FaceIDDict"""

import unittest

from PiCN.Layers.LinkLayer.FaceIDTable import FaceIDDict
from PiCN.Layers.LinkLayer.Interfaces import AddressInfo

class test_FaceIDDict(unittest.TestCase):
    """Test the FaceIDDict"""

    def setUp(self):
        self.faceidtable = FaceIDDict()

    def tearDown(self):
        pass


    def test_adding_entry_to_FaceIDTable(self):
        """test adding entries to the face table"""
        faceid1 = 3
        addr_info1 = AddressInfo("127.0.0.1", "Interface")
        self.faceidtable.add(faceid1, addr_info1)
        self.assertEqual(self.faceidtable.addrinfo_to_faceid.get(addr_info1), faceid1)
        self.assertEqual(self.faceidtable.faceid_to_addrinfo.get(faceid1), addr_info1)
        self.assertEqual(len(self.faceidtable.addrinfo_to_faceid), 1)
        self.assertEqual(len(self.faceidtable.faceid_to_addrinfo), 1)

        faceid2 = 7
        addr_info2 = AddressInfo("192.168.2.1", "Ethernet")
        self.faceidtable.add(faceid2, addr_info2)
        self.assertEqual(self.faceidtable.addrinfo_to_faceid.get(addr_info2), faceid2)
        self.assertEqual(self.faceidtable.faceid_to_addrinfo.get(faceid2), addr_info2)

        self.assertEqual(self.faceidtable.addrinfo_to_faceid.get(addr_info1), faceid1)
        self.assertEqual(self.faceidtable.faceid_to_addrinfo.get(faceid1), addr_info1)
        self.assertEqual(len(self.faceidtable.addrinfo_to_faceid), 2)
        self.assertEqual(len(self.faceidtable.faceid_to_addrinfo), 2)


    def test_get_functions(self):
        """Test the getting functions of the faceidtable"""
        r1 = self.faceidtable.get_address_info(3)
        self.assertIsNone(r1)
        r2 = self.faceidtable.get_face_id(AddressInfo("127.0.0.1", 1))
        self.assertIsNone(r2)

        faceid1 = 3
        addr_info1 = AddressInfo("127.0.0.1", 1)
        self.faceidtable.add(faceid1, addr_info1)
        faceid2 = 7
        addr_info2 = AddressInfo("192.168.2.1", 2)
        self.faceidtable.add(faceid2, addr_info2)

        r3 = self.faceidtable.get_face_id(addr_info1)
        self.assertEqual(r3, 3)

        r4 = self.faceidtable.get_address_info(r3)
        self.assertEqual(r4, addr_info1)

        r5 = self.faceidtable.get_address_info(faceid2)
        self.assertEqual(r5, addr_info2)

        r6 = self.faceidtable.get_face_id(addr_info2)
        self.assertEqual(r6, faceid2)


    def test_remove_entry(self):
        """Test the remove function"""
        faceid1 = 3
        addr_info1 = AddressInfo("127.0.0.1", 1)
        self.faceidtable.add(faceid1, addr_info1)

        faceid2 = 7
        addr_info2 = AddressInfo("192.168.2.1", 2)
        self.faceidtable.add(faceid2, addr_info2)

        self.assertEqual(len(self.faceidtable.addrinfo_to_faceid), 2)
        self.assertEqual(len(self.faceidtable.faceid_to_addrinfo), 2)

        self.faceidtable.remove(faceid2)

        self.assertEqual(len(self.faceidtable.addrinfo_to_faceid), 1)
        self.assertEqual(len(self.faceidtable.faceid_to_addrinfo), 1)

        r1 =  self.faceidtable.get_face_id(addr_info2)
        self.assertEqual(r1, None)
        r2 = self.faceidtable.get_address_info(faceid1)
        self.assertEqual(r2, addr_info1)


    def test_get_or_create_faceid(self):
        """test adding a face and automatically adding a faceid"""
        faceid1 = 0
        addr_info1 = AddressInfo("127.0.0.1", 1)
        r1 = self.faceidtable.get_or_create_faceid(addr_info1)
        self.assertEqual(r1, faceid1)
        r2 = self.faceidtable.get_address_info(faceid1)
        self.assertEqual(r2, addr_info1)

        r3 = self.faceidtable.get_or_create_faceid(addr_info1)
        self.assertEqual(r3, faceid1)

    def test_remove_oldest(self):
        """test that datastructure removes oldest entry if there is not enough space"""
        entries = []
        for i in range(0,self.faceidtable.max_entries*5):
            addr_info = AddressInfo("127.0.0.1", i)
            fid = self.faceidtable.get_or_create_faceid(addr_info)
            entries.append((fid, addr_info))

        self.assertEqual(len(self.faceidtable.faceids), self.faceidtable.max_entries)
        self.assertEqual(len(self.faceidtable.addrinfo_to_faceid), self.faceidtable.max_entries)
        self.assertEqual(len(self.faceidtable.faceid_to_addrinfo), self.faceidtable.max_entries)

        for i in range(4*self.faceidtable.max_entries,5*self.faceidtable.max_entries):
            addr_info = self.faceidtable.get_address_info(entries[i][0])
            self.assertEqual(addr_info, entries[i][1])



