## PiCN Toolbox

The PiCN toolbox (`starter/`) contains:
* `picn-relay` — ICN forwarder (`--runtime sync|async`, default sync)
* `picn-nfn` — NFN forwarder (`--runtime sync|async`)
* `picn-peek` / `picn-fetch` — fetch tools (`picn-fetch` supports `--runtime`)
* `picn-repo` / `picn-pushrepo` — repositories
* `picn-mgmt` — management client
* `picn-setup` — multi-node helper

See also [`docs/architecture.md`](architecture.md) for sync vs async runtimes.

### PiCN Forwarder

```
usage: picn-relay [-h] [-p PORT] [-f {ndntlv,simple}]
                       [-l {debug,info,warning,error,none}]
                       [--runtime {sync,async}]

optional arguments:
  -h, --help            show this help message and exit
  -p PORT, --port PORT  UDP port (default: 9000)
  -f {ndntlv,simple}, --format {ndntlv,simple}
                        Packet Format (default: ndntlv)
  -l {debug,info,warning,error,none}, --logging {debug,info,warning,error,none}
                        Logging Level (default: info)
  --runtime {sync,async}
                        Execution runtime (default: sync)
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
  --plain               plain output (writes payload to stdout or returns -2
                        for NACK)
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
usage: picn-fetch [-h] [--format {ndntlv, simple}] [--runtime {sync,async}]
                  ip port name

ICN Fetch Tool

positional arguments:
  ip                          IP addr of forwarder
  port                        UDP port of forwarder
  name                        ICN name of content to fetch

optional arguments:
  -h, --help                  Show this help message and exit
  --format {ndntlv, simple}   Packet Format (default is: ndntlv)
  --runtime {sync,async}      Execution runtime (default: sync)
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
`newface < ip >:< targetport >:< interface id >`

##### Attach forwarding rule to existing face
`newforwardingrule < name >:< faceid >`

##### Add content to cache
`newcontent < name >:< data >`

##### Shutdown instance
`shutdown`


