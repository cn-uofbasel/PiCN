# PiCN/ProgramLibs/flic.py
#   implements the FLIC producer and consumer side

# (c) 2018-01-19 <christian.tschudin@unibas.ch>

import binascii
import copy
import hashlib
from   PiCN.Packets import Name, Content
from   PiCN.Layers.PacketEncodingLayer.Encoder import NdnTlvEncoder
from   PiCN.Layers.PacketEncodingLayer.Encoder.NdnTlvEncoder import TlvEncoder, TlvDecoder

NDN_TYPE_MANIFEST = 0x990
NDN_TYPE_MANIFEST_INDEXTABLE = 0x991
NDN_TYPE_MANIFEST_DATAPTR = 0x992
NDN_TYPE_MANIFEST_MANIFESTPTR = 0x993


# ----------------------------------------------------------------------

class MkFlic():
    def __init__(self, icn, MTU=4000):
        self.icn = icn
        self.MTU = MTU

    def _mkContentChunk(self, name: Name, data: bytes):
        # input: name, payload bytes
        # output: chunk bytes
        c = Content(name, data)
        return NdnTlvEncoder().encode(c)  # and sign

    def bytesToManifest(self, name: Name, data: bytes) -> (Name, bytes):
        # input: byte array
        # output: (nameOfRootManifest, rootManifestChunk)
        # name already has an additional component (that will be dropped for
        # the non-root manifest or data nodes)

        subname = copy.deepcopy(name)
        subname._components.pop()

        # cut content in pieces
        raw = []
        while len(data) > 0:
            raw.append(data[:self.MTU])
            data = data[self.MTU:]

        # persist pieces and learn their hash pointers
        ptrs = []
        for r in raw:
            chunk = self._mkContentChunk(subname, r)
            # print(name)
            self.icn.writeChunk(subname, chunk)
            h = hashlib.sha256()
            h.update(chunk)
            ptrs.append(h.digest())
            # n = copy.copy(name)
            # n.__add__([h.digest])
            # ptrs.append(n.as_bytes())

        # create list of index tables, the M pointers will be added later
        # -> DDDDDDM -> DDDDDM -> ...
        tables = []
        while len(ptrs) > 0:
            tbl = b''  # index table
            while len(ptrs) > 0:
                # add an entry to the index table
                e = TlvEncoder()
                e.writeBlobTlv(NDN_TYPE_MANIFEST_DATAPTR, ptrs[0])
                e = e.getOutput().tobytes()
                # collect pointers as long as the manifest fits in a chunk
                if len(tbl) + len(e) + 100 > self.MTU:
                    break
                tbl += e
                ptrs = ptrs[1:]
            tables.append(tbl)

        # persist the manifests, start at the end, add the M pointers
        tailPtr = None
        while len(tables) > 0:
            tbl = tables[-1]
            if tailPtr:
                e = TlvEncoder()
                e.writeBlobTlv(self.MANIFEST_MANIFESTPTR, tailPtr)
                tbl += e.getOutput()
            m = TlvEncoder()
            m.writeBlobTlv(NDN_TYPE_MANIFEST_INDEXTABLE, tbl)
            m.writeTypeAndLength(NDN_TYPE_MANIFEST, len(m))
            if len(tables) == 1:
                subname = name  # copy.copy(name)
                # name.__add__([b'_'])
            c = Content(subname, m.getOutput())
            chunk = NdnTlvEncoder().encode(c)  # and sign
            self.icn.writeChunk(name, chunk)
            h = hashlib.sha256()
            h.update(chunk)
            tailPtr = h.digest()
            tables = tables[:-1]

        return (name, chunk)


# ----------------------------------------------------------------------

class DeFlic():
    def __init__(self, icn, decoder=None):
        self.icn = icn
        self.decoder = decoder

    def _indexTable2data(self, pfx: Name, decoder, end: int):
        # traverse the manifest tree
        # input: decoder with index table
        # output: reassembled data
        data = b''
        while decoder._offset < end:
            if decoder.peekType(NDN_TYPE_MANIFEST_DATAPTR, end):
                ptr = decoder.readBlobTlv(NDN_TYPE_MANIFEST_DATAPTR)
                # print("data ptr %s" % binascii.hexlify(ptr))
                name = copy.copy(pfx).setDigest(ptr)
                # print(name.to_json())
                chunk = self.icn.readChunk(name)
                data += NdnTlvEncoder().decode(chunk).get_bytes()
            elif decoder.peekType(NDN_TYPE_MANIFEST_MANIFESTPTR, end):
                ptr = decoder.readBlobTlv(NDN_TYPE_MANIFEST_MANIFESTPTR)
                # print("manifest ptr %s" % binascii.hexlify(ptr))
                name = copy.copy(pfx).setDigest(ptr)
                chunk = self.icn.readChunk(name)
                content = NdnTlvEncoder().decode(chunk)
                data += self._manifestToBytes(content.get_bytes())
            else:
                print("invalid index table entry")
                return data
        return data

    def _manifestToBytes(self, pfx: Name, manifest: bytes):
        # input: manifest (only the payload of the chunk)
        # output: re-assembled raw e2e bytes
        decoder = TlvDecoder(manifest)
        # print("manifestToBytes: %d bytes" % len(decoder._input))
        end = decoder.readNestedTlvsStart(NDN_TYPE_MANIFEST)
        decoder.readNestedTlvsStart(NDN_TYPE_MANIFEST_INDEXTABLE)
        data = self._indexTable2data(pfx, decoder, end)
        decoder.finishNestedTlvs(end)
        return data

    def bytesFromManifestName(self, name: Name):
        chunk = self.icn.readChunk(name)
        content = NdnTlvEncoder().decode(chunk)
        name._components.pop()  # drop the last component (e.g. '_')
        return self._manifestToBytes(name, content.get_bytes())

        # TODO:
        # def iterFromName(self, name):
        #    return DeFLIC_ITER(...)

# class DeFLIC_ITER():
#
#     def __init__(self):
#         pass
