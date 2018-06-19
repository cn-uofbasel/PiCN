""" Sample Data"""

# published as /alice/index.schema
alice_index_schema = ''.join(("doc:/alice/movies/[^/]+$\n"
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
                              "   => type:/mime/image/jpeg\n"))

# published as /alice/homebrewed/ac
ac_wrapper_desc = ''.join(("def decap:\n"
                           "    $secDek = call:/alice/homebrewed/fetchDEK(#, @id.pub)\n"
                           "    $dek = call:/crypto/lib/rsa/decrypt($secDek, @id.priv)\n"
                           "    return call:/nist/aes/decrypt(#, $dek, %mode, %padding)\n"
                           "\n"
                           "\n"
                           "def encap:\n"
                           "    $secDek = call:/alice/homebrewed/fetchDEK(#, @id.pub)\n",
                           "    $dek = call:/crypto/lib/rsa/decrypt($secDek, @id.priv\n",
                           "    sreturn call:/nist/aes/encrypt(#, $dek, %mode, %padding)\n"))
