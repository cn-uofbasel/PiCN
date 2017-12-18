# Management Interface

This page describes PiCN's HTTP-based management protocol. If your are interested in a command-line management tool, see in [runnables](runnables.md).



### Add a Face

> GET /linklayer/newface/< ip >:< targetport > HTTP/1.1\r\n\r\n

**Return:** Face ID



### Add Forwarding Rule

> GET /icnlayer/newforwardingrule/< name >:< faceid > HTTP/1.1\r\n\r\n

**Return:** ...

Use `%2F` to separate components in the name (URL Encoding for `/`)



### Add Content to Cache

> GET /icnlayer/newcontent/< name >:< data > HTTP/1.1\r\n\r\n

**Return:** ...

Use `%2F` to separate components in the name (URL Encoding for `/`)



### Shutdown

> GET /shutdown HTTP/1.1\r\n\r\n

**Return:** ...

Applies to all [runnables](runnables.md).

--- 

### URL Encoding

* [RFC 3986](https://tools.ietf.org/html/rfc3986)
* [Wikipedia](https://en.wikipedia.org/wiki/Percent-encoding)

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
