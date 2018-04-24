"""Wrapper description parsing and representation"""

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
        # extract encapsulation repice
        try:
            encap_recipe_block = re.compile("^def encap:.*", re.MULTILINE | re.DOTALL).search(str(wire_desc)).group()
            self.encap_recipe = '\n'.join(list(map(lambda l: l.strip(), str(encap_recipe_block).split('\n')[1:-1])))
        except:
            self.encap_recipe = None

        # extract encapsulation repice
        try:
            decap_recipe_block = re.compile("def decap:.*\\n\\n", re.DOTALL).match(str(wire_desc)).group()
            self.decap_recipe = '\n'.join(list(map(lambda l: l.strip(), str(decap_recipe_block).split('\n')[1:-2])))
        except:
            self.decap_recipe = None
