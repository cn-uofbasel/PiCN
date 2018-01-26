class NdnTlvPrinter(object):

    """
    Formatted printing of a NDN TLV to stdout.


    Specification:
       NDN Packet Format Specification 0.2-2 documentation
       http://named-data.net/doc/NDN-TLV/current/intro.html (January 2018)


    Example:
        0000 |  06 20 -- <type='Interest Packet', length=32>
        0002 |     07 13 -- <type='Name', length=19>
        0004 |        08 04 -- <type='GenericNameComponent', length=4>
        0006 |           74 68 69 73
        0010 |        08 02 -- <type='GenericNameComponent', length=2>
        0012 |           69 73
        0014 |        08 01 -- <type='GenericNameComponent', length=1>
        0016 |           61
        0017 |        08 04 -- <type='GenericNameComponent', length=4>
        0019 |           6E 61 6D 65
        0023 |     14 00 -- <type='MetaInfo', length=0>
        0025 |     15 07 -- <type='Content', length=7>
        0027 |        70 61 79 6C 6F 61 64

    """

    __has_blob_value = {8, 1, 10, 13, 14, 17, 12, 24, 25, 21, 23, 27, 29}
    __type_names = { 5: "Content Object Packet",
                     6: "Interest Packet",
                     7: "Name",
                     8: "GenericNameComponent",
                     1: "ImplicitSha256DigestComponent",
                     9: "Selectors",
                     10: "Nonce",
                     12: "InterestLifetime",
                     30: "ForwardingHint / Preference",
                     13: "MinSuffixComponents",
                     14: "MaxSuffixComponents",
                     15: "PublisherPublicKeyLocator",
                     16: "Exclude",
                     17: "ChildSelector",
                     18: "MustBeFresh",
                     19: "Any",
                     20: "MetaInfo",
                     21: "Content",
                     22: "SignatureInfo",
                     23: "SignatureValue",
                     24: "ContentType",
                     25: "FreshnessPeriod",
                     26: "FinalBlockId",
                     27: "SignatureType",
                     28: "KeyLocator",
                     29: "KeyDigest",
                     31: "Delegation",
                     }


    def __init__(self, wire_format:bytearray) -> None:
        """
        Formatted printing of a NDN TLV packet in wire format.
        :param wire_format: NDN TLV in wire format
        """
        self.__wire_format = wire_format


    def formatted_print(self) -> None:
        self.__position = 0
        self.__indention_level = 0
        print()
        self.__print_tlv()
        print()


    def byte_to_hex(n) -> str:
        """
        Convert a byte to string (hexadecimal representation)
        Example: 255 to FF
        :param n:    Byte (integer between 0 and 255)
        :return:     Hexadecimal representation
        """
        as_hex = hex(n)[2:]
        if len(as_hex) == 1:
            return "0" + as_hex.upper()
        else:
            return as_hex.upper()


    def print_without_newline(exp:str) -> None:
        """
        Print an expression without newline
        :param exp:   Expression to print
        :return:      None
        """
        print(exp, end="")


    def __print_indention(self) -> None:
        """
        Print indention
        :return: None
        """
        NdnTlvPrinter.print_without_newline(str(self.__position).zfill(4) + " | " + 3 * self.__indention_level * " ")


    def __print_tlv(self):
        print()
        self.__print_indention()
        type_value = self.__print_num()
        length = self.__print_num()
        NdnTlvPrinter.print_without_newline(" -- <type='{}', length={}>".format(self.__type_names[type_value], length))

        self.__indention_level += 1
        if type_value in self.__has_blob_value:
            self.__print_blob(length)
        else:
            next_tlv_start = self.__position + length
            while(self.__position < next_tlv_start):
                self.__print_tlv()
        self.__indention_level -= 1


    def __print_num(self) -> int:
        if self.__wire_format[self.__position] < 253:
            hex_value = self.__wire_format[self.__position]
            offset = 1
        elif self.__wire_format[self.__position] == 253:
            offset =  2
            raise NotImplementedError # TODO
        elif self.__wire_format[self.__position] == 254:
            offset =  4
            raise NotImplementedError # TODO
        elif self.__wire_format[self.__position] == 255:
            offset = 8
            raise NotImplementedError # TODO

        self.__position += offset
        NdnTlvPrinter.print_without_newline(" ")
        NdnTlvPrinter.print_without_newline(NdnTlvPrinter.byte_to_hex(hex_value))

        return hex_value    # TODO - convert from array to int


    def __print_blob(self, len) -> None:
        """
        Print a Blob
        :param len: length of blob
        :return: None
        """
        idx = 0
        for e in self.__wire_format[self.__position:self.__position+len]:
            if idx % 8 == 0:
                print()
                self.__print_indention()
                NdnTlvPrinter.print_without_newline(" ")
            else:
                NdnTlvPrinter.print_without_newline(" ")
            NdnTlvPrinter.print_without_newline(NdnTlvPrinter.byte_to_hex(e))
            idx += 1
        self.__position += len
