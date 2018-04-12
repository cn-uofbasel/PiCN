# PiCN Autoconfig Protocol Specification

This document describes a network protocol used for autoconfiguration of ICN
clients and repositories. Messages defined in this protocol specification are
encapsulated in [NDN packets][ndn-pack-spec].

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD",
"SHOULD NOT", "RECOMMEND", "MAY" and "OPTIONAL" in this document are to be
interpreted as described in [IETF RFC 2119][rfc2119].

## Features

This document defines a way for a CLIENT to request information about ICN
forwarders in the local network ("FORWARDER SOLICITATION"), for a SERVER to
provide such information ("FORWARDER ADVERTISEMENT").  This information MUST
contain the UDP tunnel endpoint of a forwarder, and MAY contain ICN routes
provided by this forwarder.  Additionally it MAY contain prefixes under which
REPOSITORIES can register themselves to offer a service.  These prefixes are
tagged to be either local only or globally routed.

This document defines a way for REPOSITORIES to register their services using
a prefix advertised by a SERVER ("SERVICE REGISTRATION"), and a way for the
SERVER receiving to answer with either a positive reply containing a timeout
("REGISTRATION ACK"), or a negative reply ("REGISTRATION NACK").

This document defines a way for CLIENTS to request a list of registered
REPOSITORIES from a SERVER ("SERVICE LIST SOLICITATION"), and a way for a
SERVER to respond with such a list ("SERVICE LIST").

## Roles

- A SERVER is an autoconfig entity offering information about forwarders,
    routes and/or prefixes for the registration of local repositories.  The
    SERVER functionality may be included within an ICN Forwarder itself.  A
    SERVER MUST listen for FORWARDER SOLICITATIONS and MAY respond with a
    FORWARDER ADVERTISEMENT.  A SERVER MUST listen for SERVICE REGISTRATIONS
    for prefixes it announces in its FORWARDER ADVERTISEMENT, if any, and MUST
    respond with either a REGISTRATION ACK or a REGISTRATION NACK.  A SERVER
    MUST listen for SERVICE LIST SOLICITATIONS for all prefixes it announces,
    if any, and respond with a SERVICE LIST.
- A REPOSITORY is an autoconfig entity offering any service, which may, but
    needn't be an ICN Data Repository.  It MAY send out FORWARDER SOLICITATIONS
    and receive FORWARDER ADVERTISEMENTS.  A REPOSITORY MAY send out SERVICE
    REGISTRATIONS and listen for REGISTRATION ACKS and REGISTRATION NACKS.
- A CLIENT is an autoconfig entity that does not provide its own services, but
    merely wants to use services offered by other entities, i.e. SERVERS and
    REPOSITORIES.  A CLIENT MAY send FORWARDER SOLICITATIONS and receive FORWARDER
    ADVERTISEMENTS.  A CLIENT MAY send SERVICE LIST SOLICITATIONS and listen for
    SERVICE LISTS.

## Special Names and Prefixes

- All autoconfiguration related names MUST carry the prefix "/autoconfig".
- A FORWARDER SOLICITATION interest and FORWARDER ADVERTISEMENT data packet
    MUST be sent with the name "/autoconfig/forwarders".
- A SERVICE REGISTRATION MUST use the prefix "/autoconfig/service".  A REGISTRATION
    ACK and REGISTRATION NACK MUST use the same name as the corresponding SERVICE
    REGISTRATION interest.
- A SERVICE LIST SOLICTATION MUST use the prefix "/autoconfig/services".  It MAY
    contain additional name components, which act as a prefix filter.  A SERVICE
    LIST must use the same name as the corresponding SERVICE LIST SOLICTATION
    interest.
    
## Packet Flow

### Forwarder Solicitation

```
Client/Repository                                           Server
   |                                                           |
   | ------- Broadcast Interest /autoconfig/forwarders ------> |
   |                                                           |
   | <--------- Unicast Data /autoconfig/forwarders ---------- |
   |                                                           |
   V                                                           V
```

### Service Registration

```
Repository                                                  Server
   |                                                           |
   | -- Interest /autoconfig/service/<tun>/<prefix>/<name> --> |
   |                                                           |
   | <---- Data /autoconfig/service/<tun>/<prefix>/<name> ---- |
   |                            OR                             |
   | <---- Nack /autoconfig/service/<tun>/<prefix>/<name> ---- |
   :                                                           :
   :                      BEFORE TIMEOUT:                      :
   :                                                           :
   | -- Interest /autoconfig/service/<tun>/<prefix>/<name> --> |
   |                                                           |
   | <---- Data /autoconfig/service/<tun>/<prefix>/<name> ---- |
   |                            OR                             |
   | <---- Nack /autoconfig/service/<tun>/<prefix>/<name> ---- |
   :                                                           :
   :                                                           :
   V                                                           V
```

### Service List Solicitation

```
Client                                                      Server
   |                                                           |
   | --------- Unicast Interest /autoconfig/services --------> |
   |                                                           |
   | <---------- Unicast Data /autoconfig/services ----------- |
   |                                                           |
   V                                                           V
```

## Wire Format

There are two different payload formats, one human readable and primarily
intended for testing purposes, and another in binary form, as an extension to the
[NDN TLV][ndntlv] format.  The binary format should be used whenever possible, as
NDN names can contain non-printable characters.

### Human Readable Format

The human readable format SHOULD NOT be used except for testing purposes. The human
readable format is defined by the following ABNF.  The payload used in FORWARDER
ADVERTISEMENTS is defined by the ABNF rule FORWARDER.  The payload used in
REGISTRATION ACKS is defined by the ABNF rule SERVICEACK.  The payload used in
SERVICE LISTS is defined by the ABNF rule SERVICELIST.

    NEWLINE      = %x0A
    DIGIT        = "0" / "1" / "2" / "3" / "4" / "5" / "6" / "7" / "8" / "9"
    UDP4FACE     = "udp4://" IPV4ADDR ":" UDPPORT
    UDP6FACE     = "udp6://[" IPV6ADDR "]:" UDPPORT
    FACE         = UDP4FACE / UDP6FACE
    NAMECOMP     = [ PRINTABLE_ASCII ]
    NAME         = [ "/" NAMECOMP ]
    GLOBALPREFIX = "pg:" NAME
    LOCALPREFIX  = "pl:" NAME
    ROUTE        = "r:" NAME
    FORWARDER    = FACE NEWLINE [ GLOBALPREFIX / LOCALPREFIX / ROUTE NEWLINE ]
    SERVICELIST  = [ NAME NEWLINE ]
    SERVICEACK   = DIGIT [ DIGIT ] NEWLINE

#### Example Forwarder Advertisement

1.  Client sends interest packet with name `/autoconfig/forwarders` to a broadcast
    address.
2.  Server listening on this address sends a forwarder advertisement, e.g.
    ```
    udp4://192.168.0.42:6363
    r:/ndn
    r:/local
    pl:/local
    pg:/ndn/ch/unibas/cs/cn
    
    ```

#### Example Service Registration

1.  Repository sends interest packet with name
    `/autoconfig/service/udp4://192.168.0.42:6363/local/ping`.
    Note that the URI scheme separator (`//`) in this name is not to be interpreted
    as name component separator.  Instead, `udp4://192.168.0.42:6363` is a single
    name component.
2. Server sends data packet, e.g.
    ```
    3600
    
    ```
    for a timeout of one hour.

#### Example Service List Solicitation

1.  Client sends interest packet with name `/autoconfig/services` to a server.
2.  Server sends data packet, e.g.
    ```
    /local/ping
    /local/testrepo
    /ndn/ch/unibas/cs/cn/ping
    
    ```

### Binary Format

The binary format SHOULD be preferred over the human readable format.  It is an
extension to the [NDN TLV][ndntlv] format.  It employs TLV-TYPE numbers from the
number space reserved for application use.  The following additional TLV elements
are used:

#### Forwarder Advertisement (TLV-TYPE 128)

This element encapsulates a forwarder advertisement.  It MUST contain exactly ONE
Face element, and MAY contain zero or more Route, LocalPrefix and GlobalPrefix
elements.

#### Face (TLV-TYPE 129)

This element describes an advertised face.  It MUST contain exactly ONE of the
following combinations of elements:

- An IPv4Address element, and an UDPPort element.
- An IPv6Address element, and an UDPPort element.

#### IPv4Address (TLV-TYPE 130)

This element describes an IPv4 address.  The address is represented in binary form
in Network Byte Order.  Thus, this element has a constant length of 4 bytes.

#### IPv6Address (TLV-TYPE 131)

This element describes an IPv6 address.  The address is represented in binary form
in Network Byte Order.  Thus, this element has a constant length of 16 bytes.

#### UDPPort (TLV-TYPE 132)

This element describes an UDP Port. The port is represented in binary form in
Network Byte Order.  Thus, this element has a constant length of 2 bytes.

#### Route (TLV-TYPE 133)

This element describes a prefix routed by the advertised forwarder.  It MUST contain
exactly ONE Name element, as defined in the [NDN TLV][ndntlv] format specification.

#### LocalPrefix (TLV-TYPE 134)

This element describes a prefix, which REPOSITORIES can use as a prefix for their
own name.  It MUST contain exactly ONE Name element, as defined in the
[NDN TLV][ndntlv] format specification.  A prefix announced as LocalPrefix will not
be routed by the forwarder, and will only be addressable in a local environment. 
The exact definition of "local environment" is not part of this specification, as it
may vary between specific implementations and used tunneling protocols.

#### GlobalPrefix (TLV-TYPE 135)

This element describes a prefix, which REPOSITORIES can use as a prefix for
announcing their service.  It MUST contain exactly ONE Name element, as defined in
the [NDN TLV][ndntlv] format specification.  A prefix announced as GlobalPrefix will
be routed by the forwarder, and will be addressable globally.

#### ServiceList (TLV-TYPE 136)

This element describes a list of registered services known to the SERVER.  It MUST
contain ZERO OR MORE Name elements, as defined in the [NDN TLV][ndntlv] format
specification.

#### RegistrationTimeout (TLV-TYPE 137)

This element describes the timeout (in seconds) for a service registration.  The
value is represented as a variable-length integer in Network Byte Order.

[ndn-pack-spec]: https://named-data.net/doc/NDN-packet-spec/current/
[rfc2119]: https://tools.ietf.org/rfc/rfc2119
[ndntlv]: https://named-data.net/doc/NDN-packet-spec/current/tlv.html
