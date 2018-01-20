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
import time

from PiCN                import client
from PiCN.ProgramLibs    import flic
from PiCN.Packets.Name   import Name
from PiCN.Layers.PacketEncodingLayer.Encoder import NdnTlvEncoder
import PiCN.client           as client

# ---------------------------------------------------------------------------

if __name__ == '__main__':

    icn = client.ICN()
    # repo must be running at localhost:9876
    icn.attach("127.0.0.1", 9876, 9876, 'ndn2013')

    data = bytes(random.getrandbits(8) for _ in range(16*1024 + 123))

    # store
    print("storing %d bytes via FLIC" % len(data))
    tstamp = (time.strftime('%Y%m%d-%H%M%S') + '.txt').encode('ascii')
    name = copy.copy(icn.getRepoPrefix()).__add__([tstamp])
    name, _ = flic.MkFlic(icn).bytesToManifest(name, data)

    # retrieve
    print("retrieving FLIC manifest '%s'" % name)
    data2 = flic.DeFlic(icn).bytesFromManifestName(name)

    if not data2:
        print("ERROR: no content received")
        raise IOError

    print("retrieved content: %d bytes" % len(data2))
    if data == data2:
        print("  contents match!")
    else:
        print("  contents differ :-(")

    icn.detach()

# eof
