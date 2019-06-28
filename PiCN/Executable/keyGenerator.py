"""PiCN Peek: Tool to generate and store a key pair"""

import argparse
import Crypto
from Crypto.PublicKey import RSA
from Crypto import Random
import ast



#todo dir for saving keys


def main(args):
    if args.len < 1024:
        args.len=1024

    random_generator = Random.new().read
    key = RSA.generate(args.len, random_generator)  # generate pub and priv key



    public_key = key.exportKey('DER')
    privat_key = key.exportKey('DER', 8)

    f = open('public_key', 'bw')
    f.write(public_key)
    f.close()
    f = open('privat_key', 'bw')
    f.write(privat_key)
    f.close()



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='PiCN key Generator Tool')
    parser.add_argument('-l', '--len', type=int, default=1024, help="Length of the Key, min 1024")
    parser.add_argument('-f', '--filelocation', type=str, default="", help="Location of the key files")

    args = parser.parse_args()
    main(args)