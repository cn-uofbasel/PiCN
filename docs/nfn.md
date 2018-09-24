# Named Function Networking (NFN)
Named Function Networking (NFN) provides 
* a way to encode function code in Named Data Objects (Named Function), so they can be transfered over the network, cached, etc.
* a way to call and combine Named Functions by using interest messages.
* a forwarding engine which decides where a result is computed. 

## NFN Introduction
A NFN interest consists of one or more names and maybe other data types (integer, string, etc). 
A name either refers to a function code or a data object.  

A simple NFN interest could look like:

```console
/func/combine("Hello",/data/obj1)
```

In this case we have a function **/func/combine** with two parameters.
The first parameter is a string, while the second parameter is a data name. 

NFN relies on the forwarding by using longest prefix matching, similar to ICN. 
Therefore, all components behind the first name are ignored.
Since there are two ICN names, this interest can either be forwarded to **/func/combine**
or to **/data/obj1**.

When forwarding to **/func/combine** the interest is encoded as:

```console
/func/combine/_("Hello",%2Fdata%2Fobj1)/NFN
```

When forwarding to **/data/obj1** the interest is encoded as:

```console
/data/obj1/%2Ffunc%2Fcombine("Hello",_)/NFN
```
As one can easily see, a NFN interest consists of three main parts: 
* a prefix, where each prefix is encoded into an individual name component.
* a computation, which is encoded in a single name component (we escape inner names and squash them in one name component), and contains a placeholder ("**_**") used to define where the prepended name is integraded into the computation.
* a last component to identify the interest as NFN interest (**NFN** as last component).

After a user expressed either one or the other interest, the network can reorder the interest to optimize the location, where an interest is executed. 
For example, in data centers it is often useful to forward an interest towards the input data, since input data are usually larger than the function code.

In NFN a parameter can be a NFN expression, too. Therefore, NFN supports **function chaining**.

## Encoding a Named Function in a Content Object

A Named Function contains the actual code to be executed. Popular Named Functions may be available on many content stores.

A Named Functions consists of a name, the code to be executed and some metadata to identify how to execute the named function:
```console
<Programming Language Identifier>
<entry point>
<actual code>
```

For the sandboxed Python Execution this means a sample Named Function (Name: **/func/combine**) is: 
```console
PYTHON
func
def func(a, b):
    return a + b
```
**Note:** the Named Function will be called by the **name of the data object**, not by the name of the entry point. 
The name of the entry point is used internally only, since a Named Function can internally contains multiple functions, only the entry point is exposed to the network:
```console
PYTHON
func1
def func1(a, b):
    private_func(a, b)
    
def private_func(a, b):
    return a+b
```


## Getting Started with PiCN and NFN

We provide a simple example to show how to setup NFN nodes and how to issue a computation request. 

After installing PiCN, a NFN Forwarder can be started on port 9000: 
```console
picn-nfn --port 9000 --format ndntlv -l debug
``` 
and a second one on port 9001:
```console
picn-nfn --port 9001 --format ndntlv -l debug
``` 

Next we will install a face from the first node to the second node:
```console
picn-mgmt --port 9000 newface 127.0.0.1:9001:0
``` 
and a forwarding rule with the prefix **/data**:
```console
picn-mgmt --port 9000 newforwardingrule /data:0
``` 

Now we are ready to add some content to the nodes. 

We add a named function to the first node:
```console
picn-mgmt --port 9000 newcontent "/func/combine:PYTHON
func
def func(a, b):
    return a + b
"
```
and we add a data object to the second node:

```console
picn-mgmt --port 9001 newcontent "/data/obj1:World"
"
```

Now we are ready to run a Named Function as described above:
```console
picn-fetch 127.0.0.1 9000 '/func/combine/_("Hello",%2Fdata%2Fobj1)/NFN'
``` 
or 
```console
picn-fetch 127.0.0.1 9000 '/data/obj1/%2Ffunc%2Fcombine("Hello",_)/NFN
``` 
It does not matter which name of both is chosen, since the network will decide where to compute. 
The name prepended for the user is only meaningful for the first hop. 

In both cases the result will be: **HelloWorld**. 

## Sandboxing

Sandboxing is a very important detail of the Python Execution Environment of NFN. 
We white list secure build in function to be used within named functions.
You will find a list of build-in functions in the[Python Executor](../PiCN/Layers/NFNLayer/NFNExecutor/NFNPythonExecutor.py).
If you need additionally function you have to plug then into the list:

```console
"<name of the function within the execution environment>" : <name of the function outside of NFN (must be imported before adding it to the list)>
```

