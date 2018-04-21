
import unittest

from PiCN.Playground.AssistedSharing.IndexSchema import IndexSchema
from PiCN.Playground.AssistedSharing.SampleData import alice_index_schema


class test_IndexSchema(unittest.TestCase):

    def test_create_empty(self):
        # parse
        schema = IndexSchema(alice_index_schema)


if __name__ == '__main__':
    unittest.main()
