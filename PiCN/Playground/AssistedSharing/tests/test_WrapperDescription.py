
import unittest

from PiCN.Packets.Content import Content
from PiCN.Playground.AssistedSharing.WrapperDescription import WrapperDescription


class test_WrapperDescription(unittest.TestCase):

    def test_create_empty(self):
        # wrapper description
        ac_wrapper_desc = ''.join(("def decap:\n",
                                   "    $secDek = call:/alice/homebrewed/fetchDEK(#, @id.pub)\n",
                                   "    $dek = call:/crypto/lib/rsa/decrypt($secDek, @id.priv)\n",
                                   "    return call:/nist/aes/decrypt(#, $dek, %mode, %padding)\n",
                                   "\n",
                                   "def encap:\n",
                                   "    $secDek = call:/alice/homebrewed/fetchDEK(#, @id.pub)\n",
                                   "    $dek = call:/crypto/lib/rsa/decrypt($secDek, @id.priv\n",
                                   "    sreturn call:/nist/aes/encrypt(#, $dek, %mode, %padding)\n"))
        wire_format:bytearray = Content("/alice/homebrewed/ac", ac_wrapper_desc).content

        # parse
        description = WrapperDescription(wire_format)

        # test encap_recipe
        # test decap_recipe
        decap_recipe = "$secDek = call:/alice/homebrewed/fetchDEK(#, @id.pub)\n" + \
        "$dek = call:/crypto/lib/rsa/decrypt($secDek, @id.priv)\n" + \
        "return call:/nist/aes/decrypt(#, $dek, %mode, %padding)"
        self.assertEqual(description.decap_recipe, decap_recipe)

        # test encap_recipe
        encap_recipe = "$secDek = call:/alice/homebrewed/fetchDEK(#, @id.pub)\n" + \
        "$dek = call:/crypto/lib/rsa/decrypt($secDek, @id.priv\n" + \
        "sreturn call:/nist/aes/encrypt(#, $dek, %mode, %padding)"
        self.assertEqual(description.encap_recipe, encap_recipe)


if __name__ == '__main__':
    unittest.main()
