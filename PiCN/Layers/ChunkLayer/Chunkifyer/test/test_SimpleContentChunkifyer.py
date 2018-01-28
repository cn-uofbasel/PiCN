"""Test for Simple Content Chunkifyer"""

import unittest

from PiCN.Layers.ChunkLayer.Chunkifyer import SimpleContentChunkifyer
from PiCN.Packets import Content, Name


class test_SimpleContentChunkifyer(unittest.TestCase):

    def setUp(self):
        self.chunkifyer = SimpleContentChunkifyer()

    def tearDown(self):
        pass

    def test_generate_metadata_no_next(self):
        """Test generating a simple metadata object"""
        name = Name("/test/data")

        res = self.chunkifyer.generate_meta_data(2,4,0, 0,name)

        self.assertEqual(res.name.to_string(), "/test/data")
        self.assertEqual(res.content, "mdo:/test/data/c2;/test/data/c3:")

    def test_generate_metadata_one_next(self):
        """Test generating a simple metadata object with one following"""
        name = Name("/test/data")

        res = self.chunkifyer.generate_meta_data(2,4,0,1,name)

        self.assertEqual(res.name.to_string(), "/test/data")
        self.assertEqual(res.content, "mdo:/test/data/c2;/test/data/c3:/test/data/m1")

    def test_generate_metadata_two_next(self):
        """Test generating a simple metadata object with two following"""
        name = Name("/test/data")

        res = self.chunkifyer.generate_meta_data(2,4,1,2, name)

        self.assertEqual(res.name.to_string(), "/test/data/m1")
        self.assertEqual(res.content, "mdo:/test/data/c2;/test/data/c3:/test/data/m2")

    def test_chunk_single_metadata(self):
        name = Name("/test/data")
        string = "A" * 4096 + "B" * 4096 + "C" * 4096
        content = Content(name, string)

        md, content = self.chunkifyer.chunk_data(content)

        md_name_comp = ['/test/data']
        md_data_comp = ['mdo:/test/data/c0;/test/data/c1;/test/data/c2:']

        content_name_comp = ['/test/data/c0', '/test/data/c1', '/test/data/c2']

        content_data_comp = ["A" * 4096, "B" * 4096, "C" * 4096]

        for i in range(0, len(md)):
            self.assertEqual(md[i].name.to_string(), md_name_comp[i])
            self.assertEqual(md[i].content, md_data_comp[i])

        for i in range(0, len(content)):
            self.assertEqual(content[i].name.to_string(), content_name_comp[i])
            self.assertEqual(content[i].content, content_data_comp[i])


    def test_chunk_multiple_metadata(self):
        """Test chunking metadata with three metadata objects and 10 chunks"""
        name = Name("/test/data")
        string = "A"*4096 + "B"*4096 + "C"*4096 + "D"*4096 + "E"*4096 + "F"*4096 + "G"*4096 + "H"*4096 \
                 + "I"*4096 + "J"*4000
        content = Content(name, string)

        md, chunked_content = self.chunkifyer.chunk_data(content)

        md_name_comp = ['/test/data', '/test/data/m1', '/test/data/m2']
        md_data_comp = ['mdo:/test/data/c0;/test/data/c1;/test/data/c2;/test/data/c3:/test/data/m1',
                        'mdo:/test/data/c4;/test/data/c5;/test/data/c6;/test/data/c7:/test/data/m2',
                        'mdo:/test/data/c8;/test/data/c9:']

        content_name_comp = ['/test/data/c0', '/test/data/c1', '/test/data/c2', '/test/data/c3', '/test/data/c4',
                             '/test/data/c5', '/test/data/c6', '/test/data/c7', '/test/data/c8', '/test/data/c9']

        content_data_comp = ["A"*4096, "B"*4096, "C"*4096, "D"*4096, "E"*4096, "F"*4096, "G"*4096, "H"*4096,
                             "I"*4096, "J"*4000]


        for i in range(0, len(md)):
            self.assertEqual(md[i].name.to_string(), md_name_comp[i])
            self.assertEqual(md[i].content, md_data_comp[i])

        for i in range(0, len(chunked_content)):
            self.assertEqual(chunked_content[i].name.to_string(), content_name_comp[i])
            self.assertEqual(chunked_content[i].content, content_data_comp[i])

    def test_chunk_multiple_metadata_reassemble(self):
        """Test chunking metadata with three metadata objects and 10 chunks and reassemble"""
        name = Name("/test/data")
        string = "A" * 4096 + "B" * 4096 + "C" * 4096 + "D" * 4096 + "E" * 4096 + "F" * 4096 + "G" * 4096 + "H" * 4096 \
                 + "I" * 4096 + "J" * 4000
        content = Content(name, string)

        md, chunked_content = self.chunkifyer.chunk_data(content)

        md_name_comp = ['/test/data', '/test/data/m1', '/test/data/m2']
        md_data_comp = ['mdo:/test/data/c0;/test/data/c1;/test/data/c2;/test/data/c3:/test/data/m1',
                        'mdo:/test/data/c4;/test/data/c5;/test/data/c6;/test/data/c7:/test/data/m2',
                        'mdo:/test/data/c8;/test/data/c9:']

        content_name_comp = ['/test/data/c0', '/test/data/c1', '/test/data/c2', '/test/data/c3', '/test/data/c4',
                             '/test/data/c5', '/test/data/c6', '/test/data/c7', '/test/data/c8', '/test/data/c9']

        content_data_comp = ["A" * 4096, "B" * 4096, "C" * 4096, "D" * 4096, "E" * 4096, "F" * 4096, "G" * 4096,
                             "H" * 4096,
                             "I" * 4096, "J" * 4000]

        for i in range(0, len(md)):
            self.assertEqual(md[i].name.to_string(), md_name_comp[i])
            self.assertEqual(md[i].content, md_data_comp[i])

        for i in range(0, len(chunked_content)):
            self.assertEqual(chunked_content[i].name.to_string(), content_name_comp[i])
            self.assertEqual(chunked_content[i].content, content_data_comp[i])

        reassembled_content = self.chunkifyer.reassamble_data(md[0].name, chunked_content)
        self.assertEqual(content, reassembled_content)


    def test_parse_metadata_next(self):
        """Test parse metadata with next metadata"""
        md, names = self.chunkifyer.parse_meta_data(
            "mdo:/test/data/c0;/test/data/c1;/test/data/c2;/test/data/c3:/test/data/m1")

        self.assertEqual(Name("/test/data/m1"), md)
        names_comp = [Name("/test/data/c0"), Name("/test/data/c1"), Name("/test/data/c2"), Name("/test/data/c3")]
        self.assertEqual(names, names_comp)

    def test_parse_metadata(self):
        """Test parse metadata"""
        md, names = self.chunkifyer.parse_meta_data(
            "mdo:/test/data/c0;/test/data/c1;/test/data/c2;/test/data/c3:")

        self.assertEqual(None, md)
        names_comp = [Name("/test/data/c0"), Name("/test/data/c1"), Name("/test/data/c2"), Name("/test/data/c3")]
        self.assertEqual(names, names_comp)