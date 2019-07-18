from PiCN.Packets import SignatureType
"""
    Internal representation of a signature object
    """


class Signature:

    #signature can be empty
    def __init__(self, signatureType=SignatureType.NO_SIGNATURE, identityLocator=None, identityProof=None, outputSignature=None, Signature=None, signatureSignature=None, argumentIdentifier=None ,bytarray=None):
        # input provenance can be arbitrary many
        self.signatureType=signatureType
        self.identityLocator=identityLocator
        self.identityProof=identityProof
        self.outputSignature=outputSignature
        self.argumentIdentifier=argumentIdentifier
        self.inputProvenance=Signature
        self.signatureSignature=signatureSignature
        self.bytarray=bytarray

    """

    def __init__(self):
        pass
    """


    def to_string(self)-> str:
        #todo /
        cut="\n"
        s= str(self.signatureType) + cut + str(self.identityLocator) + cut + str(self.identityProof) + cut + str(self.outputSignature) + cut + str(self.inputProvenance) + cut + str(self.signatureSignature) + cut + str(self.argumentIdentifier)
        return s

    def to_bytearray(self):
        return bytearray(self.to_string(), 'utf-8')


    def len(self):
        return len(self.to_string())-5


    # for testing
    def disp_test(self):
        if(self.signatureType==None):
            print("sig tipe=NOne")
        print("test objekt Signature: ", self.to_string())



    def signature_type_as_int(self) -> int:
        if self.signatureType==SignatureType.PROVENANCE_SIGNATURE:
            return 2
        if self.signatureType==SignatureType.DEFAULT_SIGNATURE:
            return 1
        else:
            return 0




