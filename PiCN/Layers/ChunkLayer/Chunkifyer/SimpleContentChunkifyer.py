"""A simple Chunkifyer for PiCN"""

from typing import List

from PiCN.Layers.ChunkLayer.Chunkifyer import BaseChunkifyer
from PiCN.Packets import Content, Name


class SimpleContentChunkifyer(BaseChunkifyer):

    def __init__(self, chunksize: int=4096):
        super().__init__(chunksize)
        self._num_of_names_in_metadata = 4

    def chunk_data(self, packet: Content) -> (List[Content], List[Content]):
        """Split content to chunks and generate metadata"""
        name = packet.name
        data = packet.content
        content_size = len(packet.content)
        chunks = [data[i:i + self._chunksize] for i in range(0, len(data), self._chunksize)]
        num_of_chunks = len(chunks)
        meta_data = []
        for i in range(0, num_of_chunks, self._num_of_names_in_metadata):
            endindex = min(i+self._num_of_names_in_metadata, num_of_chunks)
            md_num = int(i/self._num_of_names_in_metadata)
            next = 0
            if i + self._num_of_names_in_metadata < num_of_chunks:
                next = int(i/self._num_of_names_in_metadata)+1
            meta_data.append(self.generate_meta_data(i, endindex, md_num, next, packet.name, content_size))

        content = []
        for i in range(0, num_of_chunks):
            chunk_name = Name(name.to_string() + "/c" + str(i))
            content.append(Content(chunk_name, chunks[i]))

        return meta_data, content


    def reassamble_data(self, name: Name, chunks: List[Content]) -> Content:
        data = ""
        for d in chunks:
            data = data + d.content
        return Content(name, data)


    def generate_meta_data(self, startindex: int, endindex: int, md_num: int, next: int, name: Name, content_size: int)\
            -> Content:
        """Generate the meta data"""
        metadata = "mdo:" + str(content_size) + ":"
        for i in range(startindex, endindex):
            metadata = metadata + name.to_string() + "/c" + str(i)
            if i != endindex - 1:
                metadata = metadata + ";"
        metadata = metadata + ":"
        if next > 0:
            metadata = metadata + name.to_string() + "/m" + str(next)
        md_name = name.to_string()
        if md_num > 0:
            md_name = md_name +  "/m" + str(md_num)
        md_name_obj = Name(md_name)
        metadata_obj = Content(md_name_obj, metadata.encode('ascii'))
        return metadata_obj

    def parse_meta_data(self, data: str) -> (Name, List[Name], int):
        """parse the meta data"""
        parts = data.split(":")
        content_size = parts[1]
        chunknames = parts[2].split(";")
        next_md = parts[3]
        names = [Name(s) for s in chunknames]
        md = None
        if next_md != "":
            md = Name(next_md)
        return (md, names, content_size)


