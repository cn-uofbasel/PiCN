#!/usr/bin/env python3

import sys
sys.path.append('..')

import PiCN.client as client
import time

# ---------------------------------------------------------------------------

if __name__ == '__main__':

    icn = client.ICN()
    icn.attach("127.0.0.1", 9876)

    pfx = icn.getDefaultPrefix()
    print("Default prefix is %s" % pfx)

    name = pfx + '/' + time.strftime('')
    name = pfx + '/' + 'aha'

    icn.writeChunk(name, "my content is " + name)
    c = icn.readChunk(name)
    if c:
        print(c)
    else:
        print("ERROR: no content received")

    icn.detach()

# eof
