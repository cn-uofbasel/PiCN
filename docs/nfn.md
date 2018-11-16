# Named Function Networking (NFN)
Named Function Networking (NFN) provides 
* a way to encode function code in Named Data Objects (Named Function), so they can be transfered over the network, cached, etc.
* a way to call and combine Named Functions by using interest messages.
* a forwarding engine which decides where a result is computed. 

**Note**: NFN has a [Sandboxed Python Execution Environment](nfn.md#sandboxing).

## NFN Introduction
A NFN interest consists of one or more names and maybe other data types (integer, string, etc). 
A name either refers to a function code or a data object.  

A simple NFN interest could look like:

```console
/func/combine("Hello",/data/obj1)
```

In this tutorial we have a function **/func/combine** with two parameters.
The first parameter is a string, while the second parameter is a data name. 
In NFN a parameter can be a NFN expression, too. Therefore, NFN supports **function chaining**.

NFN relies on the forwarding by using longest prefix matching, similar to ICN. 
Therefore, all components behind the first name are ignored.
Since there are two ICN names, this interest can either be forwarded to **/func/combine**
or to **/data/obj1**.
The forwarding strategy on the nodes in the network decides, which name is prepended. Each network node can 
rewrite the name of an interest and prepend a different name or split the computation to subcomputations for parallel execution. Since the network automatically rewrites an interest message, a user do not need to care about prepending a name or parallelization.

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
```

Now we are ready to call the Named Function:
```console
picn-fetch 127.0.0.1 9000 '/func/combine("Hello",/data/obj1)/NFN'
```
The result will be: **HelloWorld**. 

## Sandboxing

Sandboxing is a very important detail of the Python Execution Environment of NFN. 
We white list secure build in function to be used within named functions.
You will find a list of build-in functions in the [Python Executor](../PiCN/Layers/NFNLayer/NFNExecutor/NFNPythonExecutor.py).
If you need additionally function you have to plug then into the list:

```console
"<name of the function within the execution environment>" : <name of the function outside of NFN (must be imported before adding it to the list)>
```

