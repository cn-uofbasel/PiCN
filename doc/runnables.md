## Runnables


### PiCN Forwarder

> python3 PiCn/Executable/ICNForwarder.py

```
usage: ICNForwarder.py [-h] [-p PORT] [-f {ndntlv,simple}]
                       [-l {debug,info,warning,error,none}]

PiCN Forwarder

optional arguments:
  -h, --help            show this help message and exit
  -p PORT, --port PORT  UDP port (default: 9000)
  -f {ndntlv,simple}, --format {ndntlv,simple}
                        Packet Format (default: ndntlv)
  -l {debug,info,warning,error,none}, --logging {debug,info,warning,error,none}
                        Logging Level (default: info)
```

### Starting a Repository

> python3 PiCn/Executable/ICNDataRepository.py < path-on-disk > < name-prefix > < listeningport >



### Fetching a single content object (without chunking)

> python3 PiCn/Executable/SimpleFetch.py < ip > < port > < name > [< wireformat >]



### Fetch a high-level object (i.e. handle chunking)

> python3 PiCn/Executable/Fetch.py < ip > < port > < name >



### Send a Management Command to an Instance

> python3 PiCn/Executable/Mgmt.py < ip > < port > < command > [ < param > ]

#### Commands and Parameters

##### Create new face
> newface < ip >:< targetport >

##### Attach forwarding rule to existing face
> newforwardingrule < name >:< faceid >

##### Add content to cache
> newcontent < name >:< data >

##### Shutdown instance
> shutdown

---

##### Wireformat

* `simple` (if not specified)
* `ndntlv`