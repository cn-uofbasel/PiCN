# client who can request data, uses reputation of contetnt provider to request data from most trustworthy node.

import argparse
import socket
import sys
import hashlib
import random
import threading
import time
import datetime
import PySimpleGUI as sg

from PiCN.ReputationSystem.Reputation import Reputation
from PiCN.ProgramLibs.Fetch import Fetch
from PiCN.Executable.Fetch import Fetch
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
from PiCN.Layers.NFNLayer.Parser import DefaultNFNParser
from PiCN.Layers.NFNLayer.NFNOptimizer import BaseNFNOptimizer

# from PiCN.Executable.VerifyProvenance import VerifyProvenance


class ReputationClient(object):

    def __init__(self, args):
        self.ReputationSystem = reputationSystem()
        self.ip = args.ip
        self.port = args.port
        self.myname = args.myname
        self.listeningServer = None
        self.window = self.createGUI(self.myname)


    # call picn-peek same arguments (ip, port, name) name is the last argument
    def reputationClientMain(self, args):
        self.startListeningThread()

        command = ""
        #print("picn-peek -i 127.0.0.1 -p 9000  /data/obj1")
        #print("picn-get-best -i 127.0.0.1 -p 9000  /obj1")
        #("picn-get-reputation-from -i 127.0.0.1 -p 9101 /user2/reputation/")
        encoder = NdnTlvEncoder()


        # endless loop waits for new commands
        while command != "quit" or command != "exit":

            #command = input("\nenter new command!: ")
            event, values = self.window.Read()
            count = 0
            #print(command)
            command = values[0]

            if command == "quit" or command == "exit" or event is None or event == 'Exit':
                break


            if len(command) > 0:
                # print(command)

                if  command[:10] == "picn-fetch":
                    print("fetch data")
                    count =5
                    (ip, port, objectName) = self.extractCommand(command)
                    whire_packet = self.handleFetch(ip, port, objectName)
                    if whire_packet != None:
                        result = self.handleReputation(whire_packet=whire_packet, encoder=encoder, objectName=objectName, ip=ip, port=port)
                    self.printResultGUI(command, result)
                    self.printReputationGUI()

                if command[:9] == "picn-peek"  :
                    count = 1
                    (ip, port, objectName) = self.extractCommand(command)
                    # name = getMosttrustworthyNode(name)
                    whire_packet = self.handlePeek(ip, port, objectName)

                    result = self.handleReputation(whire_packet=whire_packet, encoder=encoder, objectName=objectName, ip=ip, port=port)
                    self.printResultGUI(command, result)
                    self.printReputationGUI()

                # todo more fancy stuff
                if command == "print-reputation" or command == "print":

                    count = 1
                    self.printReputation()
                    self.printReputationGUI()

                if command[:15] == "picn-print-best" or command[:4] == "best":
                    count=9

                    bestEntity = self.ReputationSystem.getBestEntity()
                    if bestEntity != -1:
                        bestEntity.printNice()

                if command[:14] == "picn-from-best":
                    count = 3# find name in string
                    index = command.rfind(" ")
                    name = command[index + 1:]
                    (nameWithPrefix, ip, port, bestEntity) = self.getMostTrustworty(name)

                    if nameWithPrefix == -1:
                        print("ERROR: no nodes in reputation system, search with picn-peek or picn-fetch!")
                    else:
                        if nameWithPrefix.find("func")>0:
                            whire_packet = self.handleFetch(ip,port,nameWithPrefix)
                        else:
                            whire_packet = self.handlePeek(ip, port, nameWithPrefix)

                        # if node is trustworty enough verification is not allways needed
                        if self.verificationNeded(bestEntity) and encoder.is_content(whire_packet):
                            involvedNodes = self.verifySignature(whire_packet)
                            for (correct, keyname) in involvedNodes:
                                self.updateReputation( correct, keyname, ip, port, name)
                        else:
                            print("No verification needed.")
                        self.printReputationGUI()
                        result = self.getResult(whire_packet)
                        self.printResultGUI(command, result)

                if command[:24] == "picn-get-reputation-from":
                    #expects: in requested name "reputation"
                    count = 4
                    (ip, port, objectName) = self.extractCommand(command)
                    packet =  self.requestReputation(objectName, ip, port)
                    self.handeForeignReputation(packet)
                    self.printReputationGUI()

                if count == 0:
                    print("unkown command:")
                    print(command)
                    self.printResultGUI(command, "unkown command:")

        self.window.close()
        # end of main loop
        print("shut down server")
        self.stopListeningThread()
        print("end")

    def getResult(self, whire_packet):
        try:
            decoder = NdnTlvEncoder()
            tlvdecoder = TlvDecoder(whire_packet)
            tlvdecoder.readNestedTlvsStart(Tlv.Data)
            name = decoder.decode_name(tlvdecoder)
            meta_info = decoder.decode_meta_info(tlvdecoder)

            return tlvdecoder.readBlobTlv(Tlv.Content).tobytes()
        except():
            print("error getResult Failed")
            return 3

    def handleReputation(self, whire_packet, encoder, objectName, ip, port):
        if encoder.is_nack(whire_packet):
            print("recived nack")
        else:
            decoder = NdnTlvEncoder()
            tlvdecoder=TlvDecoder(whire_packet)
            tlvdecoder.readNestedTlvsStart(Tlv.Data)
            name = decoder.decode_name(tlvdecoder)
            meta_info = decoder.decode_meta_info(tlvdecoder)

            payload = tlvdecoder.readBlobTlv(Tlv.Content).tobytes()

            sig = decoder.decode_signature(tlvdecoder)
            # todo check if verification is needed
            index = self.ReputationSystem.searchEntity(sig.identityLocator)
            if index <0 or self.verificationNeded(self.ReputationSystem.knownEntitys[index]):
                involvedNodes = self.verifySignature(whire_packet)

                #print("recived: ", objectName)
                command = " "
                for (correct, keyname) in involvedNodes:
                    self.updateReputation(correct, keyname, ip, port, objectName)
            else:
                print("No verification needed, Node is trust worthy")
            return payload

    def verificationNeded(self, entity):
        """if hasattr(entity, 'reputation'):
            return True"""
        # if the reputation is not high enough, eg. 10, or random
        if entity.reputation < self.ReputationSystem.trustFullyVallue:
            return True
        if random.random() < 0.5:
            return True
        # todo more reasons to verify?
        return False


    def getprefix(self, name):
        # print("getprefix()")
        first = name.find("/")
        # print(first)

        if first < 0:
            return name
        second = name.find("/", first + 1)

        # print(second)

        return name[first + 1:second]

    def getNodeName(self, name):
        index = name.find("node")
        return name[index:index+5]

    def updateReputation(self, correct, keyname, ip, port, name=None):
        # print("keyname ",keyname)
        # print(correct)
        statickeyname= b'\x9cJ\xc4;\xe7pq\xa0\xaf7=\x85,\x8dl\xe9\xff\xb7\xfaX!\x90\x04A\xb5< \x074|\xf5\xc5'
        #print("update reputation")
        #print("name", name)
        #print("given key: ", keyname)
        #print("static key")

        #name = self.getprefix(name)
        name = self.getNodeName(name)
        index = self.ReputationSystem.searchEntity(keyname)

        if index < 0:
            #print("Reputationsystem add new node:   ", name)
            # not found -> new node
            self.ReputationSystem.addNewEntity(keyname, ip, port, name)
            index = self.ReputationSystem.searchEntity(keyname)
        #print(index)
        if correct:
            self.ReputationSystem.knownEntitys[index].ratePositive()
        else:
            self.ReputationSystem.knownEntitys[index].rateNegative()

        index2 = self.ReputationSystem.searchEntity(statickeyname)

        if keyname != statickeyname and correct:
            if index2 < 0:
                self.ReputationSystem.addNewEntity(statickeyname, 0, 0, "repository")
                index2 = self.ReputationSystem.searchEntity(statickeyname)
            self.ReputationSystem.knownEntitys[index2].ratePositive()

        #print("end update repsys")

    def getMostTrustworty(self, name):
        # add name prefix of the best node
        # return name with prefix, ip and port, bestEntity

        bestEntity = self.ReputationSystem.getBestEntity()
        if bestEntity == -1:
            # print("ERROR no node found in reputation system")
            return (-1, -1, -1, -1)
        nameWithPrefix = "/func/" + bestEntity.name + "/" + name

        #print("searching for: ", nameWithPrefix)
        return (nameWithPrefix, bestEntity.ip, bestEntity.port, bestEntity)




    def verifySignature(self, whirepacket, args=None):
        """
        parmam whirepacket: tlv packet
        return: array of all involved nodes:
            correct (bool): true if the provenance record is correct, false if not
            keyname: public key name of node
        """

        # decode tlv packet
        (name, payload, signature) = VerifyProvenance.decode_data(whirepacket)
        calculatedSignature = VerifyProvenance.calculate_new_signature(name, payload, signature)
        (public_key, pubkey_ca_content_obj, public_key_ca) = VerifyProvenance.extract_key(whirepacket, args)
        key_is_ok = VerifyProvenance.verify_key(pubkey_ca_content_obj)

        if not key_is_ok:
            print("Key is not korrect")
            return [(False, signature.identityLocator)]

        provenanceisOK = VerifyProvenance.verify_signature(name, payload, signature, whirepacket, args)
        if provenanceisOK:
            return [(True, signature.identityLocator)]
        else:
            return [(False, signature.identityLocator)]
        correct = False
        keyname = None

        returnarray = [(correct, keyname)]
        return returnarray


    def printReputation(self):
        print("All my Reputations:\n")
        #for rep in self.ReputationSystem.knownEntitys:
        self.ReputationSystem.print()


    def handleFetch(self, ip, port, name_str):

        name = name_str
        if 'NFN' in name_str and '_' not in name_str:
            name = self.parse_nfn_str(name_str)
        #name="'"+name+"'"
        encoder = NdnTlvEncoder()
        """
        fetchTool = Fetch(ip, port, encoder=encoder)
        content = fetchTool.fetch_data(name, timeout=10)

        print("found: ",content)
        """
        #-------------------------------------------------------------------------

        timeout = 5
        #encoder = SimpleStringEncoder()
        encoder = NdnTlvEncoder()
        # Generate interest packet
        interest: Interest = Interest(name)
        encoded_interest = encoder.encode(interest)
        
        # Send interest packet

        print("interest packet")
        self.printTLVpacket(encoded_interest)

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(timeout)
        sock.bind(("0.0.0.0", 0))
        try:
            resolved_hostname = socket.gethostbyname(ip)
        except:
            print("Resolution of hostname failed.")
            return None
        sock.sendto(encoded_interest, (resolved_hostname, int(port)))

        # Receive content object
        # print("wait for answer")
        try:
            wire_packet, addr = sock.recvfrom(8192)
        except:
            print("Timeout.")
            #sys.exit(-1)
            return None
        # print("recived:")
        self.printTLVpacket(wire_packet)

        return wire_packet


    def handlePeek(self, ip, port, name):
        """
        makes a tly packet like picn-peek
        param ip, port: of where to send
        param name: name of request
        return: wire_packet
        """
        timeout = 5

        encoded_interest = self.encodeInterest(name)

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
        #print("wait for answer")
        try:
            wire_packet, addr = sock.recvfrom(8192)
        except:
            print("Timeout.")
            sys.exit(-1)
        #print("recived:")
        self.printTLVpacket(wire_packet)

        return wire_packet

    def printTLVpacket(self, packet):
        printer = NdnTlvPrinter(packet)
        printer.formatted_print()

    def extractCommand(self, command):
        # extract ip, port, name
        # expects -i bevor ip, -p bevor port, name as last argument

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

    def correct_path_input(self, filepath):
        # correct missing / in key_content_obj_location input
        if type(filepath) is not type(None):
            if filepath[-1:] != '/':
                filepath += '/'
        return filepath


    #thread that waits for request (eg reputation from other peers) and answers with own reputation
    def thread_listening(self, arg):
        ip, port = arg
        t = threading.currentThread()
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.bind((ip, port))
        print("Server started on", ip, port)
        while getattr(t, "do_run", True):
            data, address = s.recvfrom(4096)

            print("\n\nserver recived request from", address)
            decoder = NdnTlvEncoder()
            request = decoder.decode(data)

            #only return reputation if realy requested
            if str(data).find("reputation") >= 0:

                data_to_send = self.ReputationSystem.__bytes__()
                strName= "/" + self.myname+ "reputationInfo" + str(datetime.datetime.now())+"/"
                name = Name(strName)
                encoder = NdnTlvEncoder()
                #print("name",name)
                #print(strName)
                packet = encoder.encode_data(payload= data_to_send, name= name, input_provenance=0)
                s.sendto(packet, address)

                print("sent packet with my reputation\nenter new command:")
            #self.printTLVpacket(packet)
            else:
                if str(data).find("stop") >= 0:
                    print("ERROR: received a packet that is not an interest for reputation")

        print("Server stopped:  ", ip, port)


    def startListeningThread(self):
        arg=(self.ip, self.port)
        self.listeningServer = threading.Thread(target=ReputationClient.thread_listening, args=(self,arg))
        self.listeningServer.start()
        time.sleep(0.1)
        #sleep for correct output

    def stopListeningThread(self,):
        self.listeningServer.do_run = False
        #server is blocking, send request
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((self.ip, self.port+100))
        try:
            resolved_hostname = socket.gethostbyname(self.ip)
        except:
            print("Resolution of hostname failed.")
            sys.exit(-2)
        sock.sendto(b"stop", (resolved_hostname, int(self.port)))
        #wait for server thread
        self.listeningServer.join()

    #request reputation inforamtion from other peers and update own reputation infos
    def requestReputation(self, name, destinationIP ="127.0.0.1", destinationPort=9000):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(("0.0.0.0", 9900))
        interest = self.encodeInterest(name)

        try:
            resolved_hostname = socket.gethostbyname(destinationIP)
        except:
            print("Resolution of hostname failed.")
            sys.exit(-2)
        sock.sendto(interest, (resolved_hostname, int(destinationPort)))
        # Receive content object

        try:
            wire_packet, addr = sock.recvfrom(8192)
        except:
            print("Timeout.")
            sys.exit(-1)
        return wire_packet

    def addForeignReputation(self,content):

        index1 = content.find(b"#?#")
        index2 = content.find(b"#?#", index1+1)

        brep = content[index1+3:index2]

        i1=brep.find(b"#")
        i2=brep.find(b"#",i1+1)
        i3 = brep.find(b"#", i2+1)
        i4 = brep.find(b"#", i3+1)
        i5 = brep.find(b"#", i4+1)
        i6 = brep.find(b"#", i5 + 1)
        i7 = brep.find(b"#", i6 + 2)

        key=brep[:i1]
        name= bytes.decode(brep[i1+1:i2])
        reputation= float(bytes.decode(brep[i2+1:i3]))
        negcount=int(bytes.decode(brep[i3+1:i4]))
        poscount=int(brep[i4+1:i5])
        ip=bytes.decode(brep[i5+1:i6])
        port=bytes.decode(brep[i6+1:])

        index = self.ReputationSystem.searchName(name)

        #print("index", index)

        if index == -1:
            self.ReputationSystem.addNewEntity(key,ip,port,name,reputation,negcount,poscount)
        else:

            self.ReputationSystem.updateReputationwithForeignInfo(index, key, reputation, ip, port, name, negcount, poscount)

    def handeForeignReputation(self, packet):
        #self.printTLVpacket(packet)
        decoder = NdnTlvEncoder()
        content = decoder.decode(packet)
        print("update reputation system with foreign info")
        self.printTLVpacket(packet)
        cnt=packet.count(b'#?#')

        for i in range(int(cnt/2)):
            index1 = packet.find(b"#?#")
            index2 = packet.find(b"#?#", index1 + 1)
            content = packet[index1+3:index2]
            self.addForeignReputation(content)
            packet=packet[index2+3:]


    #encode data to tlv packet
    def encode(self):
        pass

    #decode data from tlv packet
    def decode(self):
        pass

    def encodeInterest(self,name):
        # Packet encoder
        encoder = NdnTlvEncoder()
        # Generate interest packet
        interest: Interest = Interest(name)
        return encoder.encode(interest)

    def parse_nfn_str(self, name: str) -> Name:
        name = name.replace("""'""", "")
        parser = DefaultNFNParser()
        optimizer = BaseNFNOptimizer(None, None, None, None)
        if '/NFN' in name:
            name = name.replace("/NFN", "")
        ast = parser.parse(name)
        if ast is None:
            return None
        names = optimizer._get_names_from_ast(ast)
        if names is None or names == []:
            names = optimizer._get_functions_from_ast(ast)
        if names is None or names == []:
            return None
        prepend_name = Name(names[0])
        if prepend_name is None:
            return None
        name_str = optimizer._set_prepended_name(ast, prepend_name, ast)
        if name_str is None:
            return None
        res = parser.nfn_str_to_network_name(name_str)
        return res

    def createGUI(self, name):

        rep_colomn = [
            [sg.T('  ', font=14, size=(45, 9), text_color='black', background_color='white', key='Reputation0',
                  justification='left'),sg.Image(key="IMAGE0", size=(50,25))],
            [sg.T('  ', font=14, size=(45, 9), text_color='black', background_color='white', key='Reputation1',
                  justification='left'), sg.Image(key="IMAGE1", size=(50, 25))],
            [sg.T('  ', font=14, size=(45, 9), text_color='black', background_color='white', key='Reputation2',
                  justification='left'), sg.Image(key="IMAGE2", size=(50, 25))],
            [sg.T('  ', font=14, size=(45, 9), text_color='black', background_color='white', key='Reputation3',
                  justification='left'), sg.Image(key="IMAGE3", size=(50, 25))],
        ]

        layout = [[sg.Text('Enter Command:')],
                  [sg.Input(do_not_clear=False, font=14, size=(40, 4), justification='top'),
                   sg.T('', size=(40, 4),font=14, justification='left', text_color='red', background_color='white',key='Command')],
                  [sg.Button('Enter'), sg.Exit()],
                  [sg.VSeperator()],
                  [sg.Column(rep_colomn)]
        ]

        return sg.Window(name, layout)

    def printResultGUI(self, command, result):
        print(command)
        print(result)
        if type(result)==type(b" "):
            result=result.decode()
        self.window.FindElement('Command').Update(command + "\nResult: " + result)

    def printReputationGUI(self):
        res =""
        cnt =0
        for reputation in self.ReputationSystem.knownEntitys:
            if type(reputation) == type(Reputation("1", "1", "1")):
                #print(reputation)
                res += reputation.niceString()

                picname= "IMAGE"+str(cnt)
                if reputation.reputation < 50:
                    self.window[picname].update(filename='~/PiCN/docs/img/light-r.png')
                elif reputation.reputation > self.ReputationSystem.trustFullyVallue:
                    self.window[picname].update(filename='~/PiCN/docs/img/light-g.png')
                else:
                    self.window[picname].update(filename='~/PiCN/docs/img/light-y.png')

                self.window.FindElement('Reputation'+str(cnt)).Update(reputation.niceString())
                cnt += 1
        #self.window.FindElement('Reputation').Update(res)

