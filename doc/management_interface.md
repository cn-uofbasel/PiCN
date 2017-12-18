# Management Interface

This page describes PiCN's HTTP-based management protocol. If your are interested in a command-line management tool, see in [runnables](runnables.md).



### Add a Face

Instructs the [link layer](architecture.md) to create a new UDP face. 

> `GET /linklayer/newface/< ip >:< targetport > HTTP/1.1\r\n\r\n`

**Return:** Face ID



### Add Forwarding Rule

Instructs the [ICN layer](architecture.md) to add a certain forwarding rule to the forwarding information base.

> `GET /icnlayer/newforwardingrule/<prefix>:<faceid> HTTP/1.1\r\n\r\n`

**Return:** ...



### Add Content to Cache

Instructs the [ICN layer](architecture.md) to generate a certain data packet and put it into the content store.

> `GET /icnlayer/newcontent/< name >:< data > HTTP/1.1\r\n\r\n`

**Return:** ...



### Shutdown

Instructs the main process of a runnable to terminate all layers and exit. Applies to all [runnables](runnables.md).

> `GET /shutdown HTTP/1.1\r\n\r\n`

**Return:** ...

--- 

#### Notes on ICN Name Encoding

Note that some characters within a name component must be escaped. Otherwise, it would for instance not be clear whether a `/` separates two components or is a single character withing a component.
We follow the *URL Encoding* conventions to escape unsafe characters.

* [RFC 3986](https://tools.ietf.org/html/rfc3986)
* [Wikipedia](https://en.wikipedia.org/wiki/Percent-encoding)

##### Cheat Sheet

|Escaped|ASCII|
|:---:|:-:|
|`%21`|`!`|
|`%22`|`"`|
|`%23`|`#`|
|`%24`|`$`|
|`%25`|`%`|
|`%26`|`&`|
|`%27`|`'`|
|`%28`|`(`|
|`%29`|`)`|
|`%2A`|`*`|
|`%2B`|`+`|
|`%2C`|`,`|
|`%2D`|`-`|
|`%2E`|`.`|
|`%2F`|`/`|
|`%3A`|`:`|
|`%3B`|`;`|
|`%3C`|`<`|
|`%3D`|`=`|
|`%3E`|`>`|
|`%3F`|`?`|
|`%40`|`@`|
|`%5B`|`[`|
|`%5C`|`\`|
|`%5D`|`]`|
|`%7B`|`{`|
|`%7C`|`|`|
|`%7D`|`}`|
