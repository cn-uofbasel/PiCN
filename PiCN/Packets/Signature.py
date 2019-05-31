from PiCN.Packets import SignatureType
"""
    Internal representation of a signature object
    """


class Signature:

    #signature can be empty
    def __init__(self, signatureType=SignatureType.NO_SIGNATURE, identityLocator=None, identityProof=None, outputSignature=None, Signature=None, signatureSignature=None, bytarray=None):

        self.signatureType=signatureType
        self.identityLocator=identityLocator
        self.identityProof=identityProof
        self.outputSignature=outputSignature
        self.inputProvenience=Signature
        self.signatureSignature=signatureSignature
        self.bytarray=bytarray

    """

    def __init__(self):
        pass
    """


    def to_string(self)-> str:
        cut="%"
        s= str(self.signatureType) + cut + str(self.identityLocator) + cut + str(self.identityProof) + cut + str(self.outputSignature) + cut + str(self.inputProvenience) + cut + str(self.signatureSignature)
        return s

    def to_bytearray(self):
        return bytearray(self.to_string(), 'utf-8')
#TODO to_bytearray


    def disp_test(self):
        if(self.signatureType==None):
            print("sig tipe=NOne")
        print("test objekt Signature: ", self.to_string())


    def signature_type_as_int(self) -> int:
        if self.signatureType==SignatureType.PROVENIENCE_SIGNATURE:
            return 2
        if self.signatureType==SignatureType.DEFAULT_SIGNATURE:
            return 1
        else:
            return 0




