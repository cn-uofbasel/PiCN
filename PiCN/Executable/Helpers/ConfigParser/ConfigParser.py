import pytoml as toml
from pytoml.core import TomlError
import re

from PiCN.Packets.Name import Name


class CouldNotOpenConfigError(Exception):
    """ raised if configuration file can not be opened """
    pass


class CouldNotParseError(Exception):
    """ raised if configuration file can not be parsed (unvalid TOML) """
    pass


class MalformedConfigurationError(Exception):
    """ raised if configuration file is valid TOML but not a valid PiCN configuration """
    pass


class ConfigParser(object):
    def __init__(self, path: str):
        """ PiCN configuration file parser.
        :param path: Path to configuration file.
        """
        # TOML parsing
        try:
            with open(path, 'rb') as f:
                self.__conf = toml.load(f)
        except OSError:
            raise CouldNotOpenConfigError()
        except TomlError as e:
            raise CouldNotParseError() # TODO -- extract line and position from e

        # PiCN configuration syntax validation
        if "logging" in self.__conf:
            if not isinstance(self.__conf["logging"], str) or self.__conf["logging"] not in ["error", "warning", "info", "debug"]:
                raise MalformedConfigurationError("Logging must one of the strings 'error', 'warning', 'info', 'debug' or unspecified")

        if "format" in self.__conf:
            if not isinstance(self.__conf["format"], str) or self.__conf["format"] not in ["ndntlv", "simple"]:
                raise MalformedConfigurationError("Format must one of the strings 'ndntlv', 'simple' or unspecified")

        if "udp_port" in self.__conf:
            if not isinstance(self.__conf["udp_port"], int) or not (0 < self.__conf["udp_port"] <= 65535):
                raise MalformedConfigurationError("udp_port must be an valid port number")

        if "faces" in self.__conf:
            if not isinstance(self.__conf["faces"], list):
                raise MalformedConfigurationError()
            for f in self.__conf["faces"]:
                if not isinstance(f, dict):
                    raise MalformedConfigurationError()
                if not "type" in f or not "address" in f:
                    raise MalformedConfigurationError("Face must have a type and address")
                if f["type"] not in ["udp"]:
                    raise MalformedConfigurationError("Unknown face type")
                if not isinstance(f["address"], str):
                    raise MalformedConfigurationError("Invalid address of a face")
                if f["type"] == "udp":
                    addr_components = f["address"].split(':')
                    if len(addr_components) != 2:
                        raise MalformedConfigurationError("Invalid address of a udp face")
                    if not addr_components[1].isdigit() or not (0 < int(addr_components[1]) <= 65535): # TODO -- have a look here!
                        raise MalformedConfigurationError("Invalid port number of a udp face")
                    regex_ip = r"^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])$"
                    regex_dn = r"^((?=[a-z0-9-]{1,63}\.)(xn--)?[a-z0-9]+(-[a-z0-9]+)*\.)+[a-z]{2,63}$"
                    if not re.match(regex_ip, addr_components[0]) and not re.match(regex_dn, addr_components[0]):
                        raise MalformedConfigurationError("Invalid IP address or domain name of a udp face")

        if "fwdrules" in self.__conf:
            if not isinstance(self.__conf["fwdrules"], list):
                raise MalformedConfigurationError()
            for r in self.__conf["fwdrules"]:
                if not isinstance(f, dict):
                    raise MalformedConfigurationError()
                if not "prefix" in r or not "face" in r:
                    raise MalformedConfigurationError("Forwarding rule must have prefix and face")
                if not isinstance(r["prefix"], str):
                    raise MalformedConfigurationError("Invalid prefix of a forwarding rule")
                if not isinstance(r["face"], int) or r["face"] < 0 or r["face"] >= len(self.__conf["faces"]):
                    raise MalformedConfigurationError("Invalid face id of a forwarding rule")

        # extract logging, format, udp_port
        try:
            self.__logging = self.__conf["logging"]
        except:
            self.__logging = None
        try:
            self.__format = self.__conf["format"]
        except:
            self.__format = None
        try:
            self.__udp_port = self.__conf["udp_port"]
        except:
            self.__udp_port = None


        # extract faces
        def face_map(f):
            if f["type"] == "udp":
                comps = f["address"].split(':')
                return ("udp", (comps[0], int(comps[1])))
        self.__faces = list(map(face_map, self.__conf["faces"]))

        # extract fwdrules
        def fwdrules_map(r):
            try:
                return (r["face"], Name(r["prefix"]))
            except:
                raise MalformedConfigurationError("Invalid prefix of a forwarding rule (not a name)")
        self.__fwdrules = list(map(fwdrules_map, self.__conf["fwdrules"]))

    @property
    def logging(self) -> str:
        """ Get log level
        :return: Log level as string ('error', 'warning', 'info', 'debug') or None (if unspecified)
        """
        return self.__logging

    @property
    def format(self) -> str:
        """ Get packet format
        :return: Packet format as string ('ndntlv', 'simple') or None (if unspecified)
        """
        return self.__format

    @property
    def udp_port(self) -> int:
        """ Get udp port
        :return: UDP port as integer or None (if unspecified)
        """
        return self.__udp_port

    @property
    def faces(self) -> list:
        """ Get all faces as a list of (type, address) tuples. Type is currently always 'udp' (though this might change
        in future); address for a udp faces is a (IP address, port number) tuple. Implicit, each face has an identifier
        which is used by forwarding rules. The ID of each face is the position in the list (starting with 0 for the
        first entry).
        Example: [('udp', ('127.0.0.1', 8000)), ('udp', ('dmi-ndn-testbed1.dmi.unibas.ch', 6363))]
        """
        return self.__faces

    @property
    def fwdrules(self) -> list:
        """ Get all forwarding rules as a list of (face ID, Name) tuples. """
        return self.__fwdrules
