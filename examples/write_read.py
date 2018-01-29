#!/usr/bin/env python3

# examples/write_read.py
#
#  this is a demo of using the PiCN client lib for
#  first writing then reading from the local repo (must be running)
#
# (c) 2018-01-18 <christian.tschudin@unibas.ch>

import copy
import sys
sys.path.append('..')

import ProgramLibs.Client.client as client
import time

# ---------------------------------------------------------------------------

if __name__ == '__main__':

    icn = client.ICN()
    # repo must be running at localhost:9876
    icn.attach("127.0.0.1", 9876, 9876, 'ndn2013')

    pfx = icn.getRepoPrefix()
    name = copy.copy(pfx)
    tstamp = time.strftime('%Y%m%d-%H%M%S') + '.txt'
    name.__add__([tstamp.encode('ascii')])

    content = "my content is known under <%s>" % name.to_string()
    icn.writeChunk(name, content.encode('ascii'))

    c = icn.readChunk(name)
    if c:
        print("retrieved content: %s" % c)
    else:
        print("ERROR: no content received")
        raise IOError

    icn.detach()

# eof
