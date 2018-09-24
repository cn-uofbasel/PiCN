# Named Function Networking (NFN)
Named Function Networking (NFN) provides 
* a way to encode function code in Named Data Objects (Named Function), so they can be transfered over the network, cached, etc.
* a way to call and combine Named Functions by using interest messages.
* a forwarding engine which decides where a result is computed. 

## NFN Encoding
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

  