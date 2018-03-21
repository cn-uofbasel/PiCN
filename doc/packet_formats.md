# Packet Formats

PiCN tools and nodes can operate with different packet formats. At the moment, the following formats are available:

* `ndntlv` (default)
* `simple`

### NDN Packet Fomat and Link Protocol (`ndntlv`)

#### Specification

* [NDN Packet Format Specification 0.2-2](http://named-data.net/doc/NDN-packet-spec/current)
* [NDN Link Protocol v2](https://redmine.named-data.net/projects/nfd/wiki/NDNLPv2)

#### Implementation Status

Partial

#### Extensions

Additional NACK reasons (link protocol):

| Value | Reason                   | Description                                |
|-------|--------------------------|--------------------------------------------|
| 160   | `NO_CONTENT`             | No content available                       |
| 161   | `COMP_QUEUE_FULL`        | No resources to perform computation        |
| 162   | `COMP_PARAM_UNAVAILABLE` | One or many input data is unavailable      |
| 163   | `COMP_EXCEPTION`         | An excpetion occured during computation    |
| 164   | `COMP_TERMINATED`        | computation terminated by computing entity |

### Simple (`simple`)

String-based and human-readable packet format. For debug-purposes only.

