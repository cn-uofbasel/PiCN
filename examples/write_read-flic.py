#!/usr/bin/env python3

# examples/write_read-flic.py
#
#  this is a demo of using the PiCN client lib for
#  first writing then reading FLICed data from the local repo (must be running)
#
# (c) 2018-01-19 <christian.tschudin@unibas.ch>

import copy
import random
import sys
sys.path.append('..')

from PiCN.Packets.Name import Name
from PiCN.Layers.PacketEncodingLayer.Encoder import NdnTlvEncoder
from PiCN.ProgramLibs.Flic.content2flic import MkFlic
from PiCN.ProgramLibs.Flic.flic2content import DeFlic
import PiCN.client as client
import time

# ---------------------------------------------------------------------------

if __name__ == '__main__':

    icn = client.ICN()
    # repo must be running at localhost:9876
    icn.attach("127.0.0.1", 9876, 9876, 'ndn2013')

    data = bytes(random.getrandbits(8) for _ in range(16*1024 + 123))
    print("storing %d bytes" % len(data))
    mkFlic = MkFlic(icn)

    pfx = icn.getRepoPrefix()
    name = copy.copy(pfx)
    tstamp = time.strftime('%Y%m%d-%H%M%S') + '.txt'
    name.__add__([tstamp.encode('ascii')])

    name, rootManifest = mkFlic.bytesToManifest(name, data)

    deFlic = DeFlic(icn)
    chunk = icn.readChunk(name)
    content = NdnTlvEncoder().decode(chunk)
    name._components.pop()
    data2 = deFlic.manifestToBytes(name, content.get_bytes())

    if data2:
        print("retrieved content: %d bytes" % len(data2))
        if data == data2:
            print("  contents match!")
        else:
            print("  contents differ :-(")
    else:
        print("ERROR: no content received")
        raise IOError

    icn.detach()

# eof
