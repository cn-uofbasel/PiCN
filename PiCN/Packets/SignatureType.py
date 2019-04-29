from enum import Enum


class SignatureType(Enum):
    """
    Enumeration for Signature Type
    """

    NO_SIGNATURE = 0

    DEFAULT_SIGNATURE = 1

    PROVENIENCE_SIGNATURE = 2

    #NoSignature="test"