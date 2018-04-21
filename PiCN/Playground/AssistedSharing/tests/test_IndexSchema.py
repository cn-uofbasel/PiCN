
import unittest

from PiCN.Playground.AssistedSharing.IndexSchema import IndexSchema


class test_IndexSchema(unittest.TestCase):

    def test_create_empty(self):
        # schema as usually retrieved from network
        wire_schema =  ("doc:/alice/movies/[^/]+\n"
                        "   -> wrapper:/irtf/icnrg/flic\n"
                        "   -> wrapper:/alice/homebrewed/ac\n"
                        "       mode='CBC'\n"
                        "       padding='PKCS5'\n"
                        "    => type:/mime/video/webm\n"
                        "\n"
                        "doc:/alice/public/docs/.*[.]pdf$\n"
                        "   -> wrapper:/simple/chunking\n"
                        "   => type:/mime/application/pdf\n")
        # parse
        schema = IndexSchema(wire_schema)


if __name__ == '__main__':
    unittest.main()
