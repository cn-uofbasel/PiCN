from PiCN.Packets import SignatureType
"""
    Internal representation of a signature object
    """


class Signature:

    #signature can be empty
    def __init__(self, signatureType=SignatureType.NO_SIGNATURE, identityLocator=None, identityProf=None, outputSignature=None, Signature=None, signatureSignature=None, bytarray=None):

        self.signatureType=signatureType
        self.identityLocator=identityLocator
        self.identityProf=identityProf
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
        s=str(self.signatureType)+cut+str(self.identityLocator)+cut+str(self.identityProf)+cut+str(self.outputSignature)+cut+str(self.inputProvenience)+cut+str(self.signatureSignature)
        return s


    def disp_test(self):
        if(self.signatureType==None):
            print("sig tipe=NOne")
        print("test objekt Signature: ", self.signatureType)






