## PiCN Toolbox

The PiCN toolbox contains:
* `picn-relay`
* `picn-peek`
* `picn-repo`
* `picn-fetch`
* `picn-mgmt`

### PiCN Forwarder

```
usage: picn-relay [-h] [-p PORT] [-f {ndntlv,simple}]
                       [-l {debug,info,warning,error,none}]

optional arguments:
  -h, --help            show this help message and exit
  -p PORT, --port PORT  UDP port (default: 9000)
  -f {ndntlv,simple}, --format {ndntlv,simple}
                        Packet Format (default: ndntlv)
  -l {debug,info,warning,error,none}, --logging {debug,info,warning,error,none}
                        Logging Level (default: info)
```


### Fetching a single content object (without chunking)

```
usage: picn-peek [-h] [-i IP] [-p PORT] [-f {ndntlv,simple}] name

positional arguments:
  name                  CCN name of the content object to fetch

optional arguments:
  -h, --help            show this help message and exit
  -i IP, --ip IP        IP address or hostname of forwarder (default: 127.0.0.1)
  -p PORT, --port PORT  UDP port (default: 9000)
  -f {ndntlv,simple}, --format {ndntlv,simple}
                        Packet Format (default: ndntlv)
```


### Starting a Repository

```
usage: picn-repo [-h] [--format FORMAT] datapath icnprefix port

ICN Data Repository

positional arguments:
  datapath         filesystem path where the repo stores its data
  icnprefix        prefix for all content stored in this repo
  port             the repo's UDP and TCP port (TCP only for MGMT)

optional arguments:
  -h, --help       show this help message and exit
  --format FORMAT
```


### Fetch a high-level object (i.e. handle chunking)

```
usage: picn-fetch [-h] [--format {ndntlv, simple}] ip port name

ICN Fetch Tool

positional arguments:
  ip                          IP addr of forwarder
  port                        UDP port of forwarder
  name                        ICN name of content to fetch

optional arguments:
  -h, --help                  Show this help message and exit
  --format {ndntlv, simple}   Packet Format (default is: ndntlv)
```


### Send a Management Command to an Instance

```
usage: picn-mgmt [-h] [-i IP] [-p PORT]
               {shutdown,getrepoprefix,getrepopath,newface,newforwardingrule,newcontent}
               [parameters]

Management Tool for PiCN Forwarder and Repo

positional arguments:
  {shutdown,getrepoprefix,getrepopath,newface,newforwardingrule,newcontent}   Management Command
  parameters                                                                  Command Parameter

optional arguments:
  -h, --help                                                                  show this help message and exit
  -i IP, --ip IP                                                              IP address or hostname of forwarder (default: 127.0.0.1)
  -p PORT, --port PORT                                                        UDP port of forwarder(default: 9000)

```

#### Management Commands and Parameters

##### Create new face
`newface < ip >:< targetport >`

##### Attach forwarding rule to existing face
`newforwardingrule < name >:< faceid >`

##### Add content to cache
`newcontent < name >:< data >`

##### Shutdown instance
`shutdown`


