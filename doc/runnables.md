## Runnables

### Forwarder
python PiCn/Executable/ICNForwarder.py < listeningport >

### Repository
python PiCn/Executable/ICNDataRepository.py < path on disk > < ICN prefix > < listeningport >


### Simple Fetch
python PiCn/Executable/Fetch.py < ip > < port > < name >

### Fetch (with chunk support)
python PiCn/Executable/Fetch.py < ip > < port > < name >

### Mgmt
python PiCn/Executable/Mgmt.py < ip > < port > < command > [ < param > ]

command: (newface < ip >:< targetport > | newforwardingrule < name >:< faceid > | newcontent < name >:< data > | shutdown)
