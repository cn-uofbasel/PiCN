
import unittest

from PiCN.Playground.AssistedSharing.IndexSchema import IndexSchema


class test_IndexSchema(unittest.TestCase):

    def test_create_empty(self):
        # index schema
        alice_index_schema = ("doc:/alice/movies/[^/]+$\n"
                              "   -> wrapper:/irtf/icnrg/flic\n"
                              "   -> wrapper:/alice/homebrewed/ac\n"
                              "       mode='CBC'\n"
                              "       padding='PKCS5'\n"
                              "    => type:/mime/video/mp4\n"
                              "\n"
                              "doc:/alice/public/docs/.*[.]pdf$\n"
                              "   -> wrapper:/simple/chunking\n"
                              "   => type:/mime/application/pdf\n"
                              "\n"
                              "doc:/alice/public/img/basel.jpg$\n"
                              "   -> wrapper:/simple/chunking\n"
                              "   => type:/mime/image/jpeg\n")

        # parse
        schema = IndexSchema(alice_index_schema)

        # match rule 1
        self.assertTrue(schema.find_matching_rule("/alice/movies/cats-and-dogs.mp4") is not None)
        self.assertTrue(schema.find_matching_rule("/foo/alice/movies/cats-and-dogs.mp4") is None)
        self.assertTrue(schema.find_matching_rule("/alice/movies/foo/cats-and-dogs.mp4") is None)

        # match rule 2
        self.assertTrue(schema.find_matching_rule("/alice/public/docs/interesting-book.pdf") is not None)
        self.assertTrue(schema.find_matching_rule("/alice/public/docs/novels/interesting-book.pdf") is not None)
        self.assertTrue(schema.find_matching_rule("/alice/public/docs/interesting-book.pdf/foo") is None)
        self.assertTrue(schema.find_matching_rule("/alice/public/interesting-book.pdf") is None)

        # match rule 3
        self.assertTrue(schema.find_matching_rule("/alice/public/img/basel.jpg") is not None)
        self.assertTrue(schema.find_matching_rule("/alice/public/img/basel.gif") is None)
        self.assertTrue(schema.find_matching_rule("/alice/public/img/2018/basel.png") is None)
        self.assertTrue(schema.find_matching_rule("/alice/public/img/basel.png/foo") is None)


if __name__ == '__main__':
    unittest.main()
