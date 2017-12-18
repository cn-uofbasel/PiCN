# Management Interface

PiCN offers a HTTP-based management interface. 

### Add a Face

> GET /linklayer/newface/< ip >:< targetport > HTTP/1.1\r\n\r\n

### Add Forwarding Rule

> GET /icnlayer/newforwardingrule/< name >:< faceid > HTTP/1.1\r\n\r\n

Use `%2F` to separate components in the name (URL Encoding for `/`)

### Add Content to the Content Store

> GET /icnlayer/newcontent/< name >:< data > HTTP/1.1\r\n\r\n

Use `%2F` to separate components in the name (URL Encoding for `/`)

### Shutdown

> GET /shutdown HTTP/1.1\r\n\r\n

Applies to all [runnables](runnables.md).