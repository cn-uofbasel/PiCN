"""Wrapper description parsing and representation"""

from itertools import groupby
import re

from PiCN.Packets.Name import Name


class WrapperDescription(object):
    """ Representation of a wrapper description"""

    """
    def decap:
        $secDek = call:/alice/homebrewed/fetchDEK(#, @id.pub)
        $dek = call:/crypto/lib/rsa/decrypt($secDek, @id.priv)
        return call:/nist/aes/decrypt(#, $dek, %mode, %padding)

    def encap:
        $secDek = call:/alice/homebrewed/fetchDEK(#, @id.pub)
        $dek = call:/crypto/lib/rsa/decrypt($secDek, @id.priv)
        return call:/nist/aes/encrypt(#, $dek, %mode, %padding)
    """

    def __init__(self, wire_desc: bytearray):
        """
        Create wrapper description object from network representation
        :param wire_desc: Wrapper description as retrieved from network
        """
        self.encap_recipe = "todo" # todo
        self.decap_recipe = "todo" # todo
