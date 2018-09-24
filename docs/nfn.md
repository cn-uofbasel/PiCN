# Named Function Networking (NFN)
Named Function Networking (NFN) provides 
* a way to encode function code in Named Data Objects (Named Function), so they can be transfered over the network, cached, etc.
* a way to call and combine Named Functions by using interest messages.
* a forwarding engine which decides where a result is computed. 

## NFN Encoding
A NFN interest consists of one or more names and maybe other data types (integer, string, etc). 
A name either refers to a function code or a data object.  
