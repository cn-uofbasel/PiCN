""" Sample Data"""

alice_index_schema = ("doc:/alice/movies/[^/]+\n"
                      "   -> wrapper:/irtf/icnrg/flic\n"
                      "   -> wrapper:/alice/homebrewed/ac\n"
                      "       mode='CBC'\n"
                      "       padding='PKCS5'\n"
                      "    => type:/mime/video/webm\n"
                      "\n"
                      "doc:/alice/public/docs/.*[.]pdf$\n"
                      "   -> wrapper:/simple/chunking\n"
                      "   => type:/mime/application/pdf\n")