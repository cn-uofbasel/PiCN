# Hello World!

Make sure that you have Python 3.6+ installed on your machine. In case case of doubt have a look at the output of:

> `python -V`



## Getting Started as a User

**Clone the Repository**

Download the latest version of PiCN to your machine:

> `git clone https://github.com/cn-uofbasel/PiCN.git`

If you run that command in your home directory, the root of PiCN is `~/PiCN`. In case you decided to clone to another directory, adjust the following commands accordingly.


**Run Unit Tests (optional)**

> `python setup.py test`

or

> `python setup.py nosetests`


**Next Steps**

Congratulations, PiCN runs on your machine! If you want to learn more, go to the [tutorial](tutorial.md).  



## Getting Started as a Developer

If you do not yet have a favourite Python IDE, we recommend you to try [PyCharm (Community Edition)](https://www.jetbrains.com/pycharm/download).

**1. Clone the Repository**

> `git clone https://github.com/cn-uofbasel/PiCN.git`


**2. Run PyCharm**


**3. Open PiCN project in PyCharm**

![PyCharm Open 1](https://raw.githubusercontent.com/cn-uofbasel/PiCN/master/doc/img/pycharm-open-1.png "PyCharm Open 1")

![PyCharm Open 2](https://raw.githubusercontent.com/cn-uofbasel/PiCN/master/doc/img/pycharm-open-2.png "PyCharm Open 2")

Note: Select the root of the cloned git repository.


**3. Mark Sources Root (Optional)**

On some systems it is necessary to mark the root folder of the python sources in PyCharm. If the following step fails, try:
 * Right-click the root python packet (`PiCN`) in the project outline.
 * Select `Mark directory as..` -> `Sources Root`
 
 
**4. Start a CCN Forwarder**
 
 * Right-click the file `PiCN.Executable.ICNForwarder.py` in the project outline
 * Select `Run ''ICNForwarder'`
 * If you see following output in the tool bar, a forwarder is running (UDP face on port 9000):
 
 ![PyCharm Relay](https://raw.githubusercontent.com/cn-uofbasel/PiCN/master/doc/img/pycharm-run-relay.png "PyCharm Open 2")


**Next Steps**

Nice, your development environment is ready! If you want to learn more about how to setup an entire network, read the [Tutorial](tutorial.md). If you want to understand the internals of PiCN go to [Architecture](architecture.md).
