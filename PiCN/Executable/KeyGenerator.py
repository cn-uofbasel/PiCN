"""PiCN Peek: Tool to generate and store a key pair"""

import argparse
import Crypto
from Crypto.PublicKey import RSA
from Crypto import Random
import ast
import os, sys


def main(args):

    #correct missing / in filelocation input
    if type(args.filelocation) is not type(None):
        if args.filelocation[-1:] is not '/':
            args.filelocation+='/'

    if args.len < 1024:
        print("Key length to smal, set to 1024.")
        args.len=1024

    random_generator = Random.new().read
    key = RSA.generate(args.len, random_generator)  # generate pub and priv key

    """
    public_key = key.exportKey('DER')
    private_key = key.exportKey('DER', 8)
    """

    public_key = key.publickey().exportKey('PEM').decode('ascii')
    private_key = key.exportKey('PEM').decode('ascii')


    if args.filelocation is None:
        #relative path
        fileDir = os.path.dirname(os.path.abspath(__file__))
        #print(fileDir)
        parentDir = os.path.dirname(fileDir)
        #print(parentDir)

        newPath = os.path.join(parentDir, 'keys')  # Get the directory for StringFunctions
        #print(newPath)
        newPath+='/'
        #sys.path.append(newPath)  # Add path into PYTHONPATH
    else:
        newPath=args.filelocation

    if (os.path.isfile(newPath+'key.pub') or os.path.isfile(newPath+'key.pub')) and args.overwrite is False:
        print("Key file already exists. \nChange filelocation or allow to overwrite!\nNo keys generated!")
        exit()

    f = open(newPath+'key.pub', 'w')
    f.write(public_key)
    print("Public key saved to " +newPath+'key.pub')
    f.close()
    f = open(newPath+'key.priv', 'w')
    f.write(private_key)
    print("Private key saved to "+newPath+'key.priv')
    f.close()
    print("Done.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='PiCN Key Generator Tool')
    parser.add_argument('-l', '--len', type=int, default=1024, help="Length of the Key, (default: 1024, minimal: 1024, multiple of 256)")
    parser.add_argument('-f', '--filelocation', type=str, help="Location of the key files (default: /PiCN/keys/)")
    parser.add_argument('-o', '--overwrite', action='store_true', help="Overwrite keys (if already existing)")

    args = parser.parse_args()
    main(args)
