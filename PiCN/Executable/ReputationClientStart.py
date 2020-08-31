# client who can request data, uses reputation of contetnt provider to request data from most trustworthy node.

import argparse
import socket
import sys
import hashlib
import random


from PiCN.ReputationSystem.ReputationSystem import reputationSystem
from PiCN.Layers.PacketEncodingLayer.Encoder import SimpleStringEncoder
from PiCN.Layers.PacketEncodingLayer.Encoder import NdnTlvEncoder
from PiCN.Layers.PacketEncodingLayer.Printer.NdnTlvPrinter import NdnTlvPrinter
from PiCN.Packets import Interest, Content
import os
from PiCNExternal.pyndn.encoding.tlv.tlv.tlv import Tlv
from PiCNExternal.pyndn.encoding.tlv.tlv.tlv_encoder import TlvEncoder
from PiCNExternal.pyndn.encoding.tlv.tlv.tlv_decoder import TlvDecoder
from PiCN.Packets import Packet, Content, Interest, Nack, NackReason, Name, UnknownPacket, Signature, SignatureType
import VerifyProvenance
#from PiCN.Executable.VerifyProvenance import VerifyProvenance

# call picn-peek same arguments (ip, port, name) name is the last argument
def reputationClientMain(args, reputationSystem):
    command = ""
    print("picn-peek -i 127.0.0.1 -p 9000  /data/obj1")
    print("picn-get-best -i 127.0.0.1 -p 9000  /obj1")
    encoder = NdnTlvEncoder()

    # endless loop waits for new commands
    while command != "quit":

        #todo remove
        #command = "picn-peek -i 127.0.0.1 -p 9000  /data/obj1"
        command = input("enter new command!: ")
        count=0
        if len(command) > 0:
            #print(command)

            if command[:9] == "picn-peek":
                count =1
                (ip, port, objectName) = extractPeek(command)
                #name = getMosttrustworthyNode(name)
                whire_packet = handlePeek(ip, port, objectName)
                involvedNodes = verifySignature(whire_packet)

                print("recived: ", objectName)

                for (correct, keyname) in involvedNodes:
                    reputationSystem = updateReputation(reputationSystem, correct, keyname, ip, port, objectName)

                # todo more fancy stuff
            if command == "print-reputation":
                count =1
                printReputation(reputationSystem)

            if command[:13] == "picn-get-best":
                count =3
                (ip, port, name) = extractPeek(command)
                (nameWithPrefix, ip, port, bestEntity) = getMostTrustworty(reputationSystem, name)

                if nameWithPrefix == -1:
                    print("ERROR: no nodes in reputation system, search with picn-peek!")
                else:
                    whire_packet = handlePeek(ip, port, nameWithPrefix)

                    #if node is trustworty enough verification is not allways needed
                    if verificationNeded(reputationSystem, bestEntity) and encoder.is_content(whire_packet):
                        involvedNodes = verifySignature(whire_packet)
                        for (correct, keyname) in involvedNodes:
                            reputationSystem = updateReputation(reputationSystem, correct, keyname, ip, port, objectName)
                    else:
                        print("No verification needed.")

            if command == "getReputationfromUser":
                count =4

            if count == 0:
                print("unkown command:")
    #end of main loop

def verificationNeded(reputationSystem, bestEntity):
    #if the reputation is not high enough, eg. 10, or random
    if bestEntity.reputation < 2:
        return True
    if random.random() < 0.1:
        return True
    #todo more reasons to verify?
    return False

def getprefix(name):
    #print("getprefix()")
    first = name.find("/")
    #print(first)

    if first < 0:
        return name
    second = name.find("/", first+1)

    #print(second)

    return name[first+1:second]


def updateReputation(reputationSystem, correct, keyname, ip, port, name = None):

    #print("keyname ",keyname)
    #print(correct)
    name = getprefix(name)
    print("new name:   ", name)

    index = reputationSystem.searchEntity(keyname)

    print(index)
    if index < 0:
        # not found -> new node
        reputationSystem.addNewEntity(keyname, ip, port, name)
        index = reputationSystem.searchEntity(keyname)
    print(index)
    if correct:
        reputationSystem.knownEntitys[index].ratePositive()
    else:
        reputationSystem.knownEntitys[index].rateNegative()
    return reputationSystem

def getMostTrustworty(reputationSystem, name):
    # add name prefix of the best node
    #return name with prefix, ip and port, bestEntity

    bestEntity = reputationSystem.getBestEntity()
    if bestEntity == -1:
        #print("ERROR no node found in reputation system")
        return (-1,-1,-1,-1)
    nameWithPrefix= "/" + bestEntity.name + name

    print("searching for: ", nameWithPrefix)
    return (nameWithPrefix, bestEntity.ip, bestEntity.port, bestEntity)



def getMosttrustworthyNode():
    pass


def verifySignature(whirepacket):
    """
    parmam whirepacket: tlv packet
    return: array of all involved nodes:
        correct (bool): true if the provenance record is correct, false if not
        keyname: public key name of node
    """

    #decode tlv packet
    (name, payload, signature) = VerifyProvenance.decode_data(whirepacket)
    calculatedSignature = VerifyProvenance.calculate_new_signature(name,  payload, signature)
    (public_key, pubkey_ca_content_obj, public_key_ca) = VerifyProvenance.extract_key(whirepacket, args)
    key_is_ok = VerifyProvenance.verify_key(pubkey_ca_content_obj)

    if not key_is_ok:
        print("Key is not korrect")
        return [(False,signature.identityLocator)]

    provenanceisOK = VerifyProvenance.verify_signature(name, payload, signature, whirepacket, args)
    if provenanceisOK:
        return [(True, signature.identityLocator)]
    else:
        return [(False, signature.identityLocator)]
    correct = False
    keyname = None

    returnarray=[(correct, keyname)]
    return returnarray

def printReputation(reputationSystem):
    print("Reputation:\n")
    for rep in reputationSystem.knownEntitys:
        reputationSystem.printReputation(rep)



def handlePeek(ip, port, name):
    """
    makes a tly packet like picn-peek
    param ip, port: of where to send
    param name: name of request
    return: wire_packet
    """
    timeout = 5

    # Packet encoder
    encoder = NdnTlvEncoder()
    # Generate interest packet
    interest: Interest = Interest(name)
    encoded_interest = encoder.encode(interest)

    # Send interest packet
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(timeout)
    sock.bind(("0.0.0.0", 0))
    try:
        resolved_hostname = socket.gethostbyname(ip)
    except:
        print("Resolution of hostname failed.")
        sys.exit(-2)
    sock.sendto(encoded_interest, (resolved_hostname, int(port)))

    # Receive content object
    try:
        wire_packet, addr = sock.recvfrom(8192)
    except:
        print("Timeout.")
        sys.exit(-1)

    printer = NdnTlvPrinter(wire_packet)
    printer.formatted_print()
    return wire_packet


def extractPeek(command):
    #extract ip, port, name
    #expects -i bevor ip, -p bevor port, name as last argument
    #print("picn-peek...")
    #print(command)

    # find ip in string
    index = command.find("-i", 9)
    start = command.find(" ", index + 2)
    end = command.find(" ", start + 1)
    ip = command[start + 1:end]
    # find port in string
    index = command.find("-p", 9)
    start = command.find(" ", index + 2)
    end = command.find(" ", start + 1)
    port = command[start + 1:end]
    # find name in string
    index = command.rfind(" ")
    name = command[index + 1:]
    """
    print(index)
    print(start)
    print(end)
    print(command[start+1:end])
    
    print("\nfound:")
    print("ip:\n",ip)
    print("port:\n",port)
    print("name:\n",name)
    """
    return ip, port, name



def correct_path_input(filepath):
    # correct missing / in key_content_obj_location input
    if type(filepath) is not type(None):
        if filepath[-1:] != '/':
            filepath += '/'
    return filepath


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='client who ceeps track of the reputation of other nodes')
    args = parser.parse_args()
    reputationSystem = reputationSystem()
    reputationClientMain(args, reputationSystem)
