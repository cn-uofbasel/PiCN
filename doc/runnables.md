## Runnables


### Starting a Forwarder

> python3 PiCn/Executable/ICNForwarder.py < listeningport >



### Starting a Repository

> python3 PiCn/Executable/ICNDataRepository.py < path-on-disk > < name-prefix > < listeningport >



### Fetching a single content object (without chunking)

> python3 PiCn/Executable/Fetch.py < ip > < port > < name >



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