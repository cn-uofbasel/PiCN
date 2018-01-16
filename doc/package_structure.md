# Package Structure

Package Structure of PiCN.

### PiCN

* **`Executable`**: *This package contains starter scripts for network nodes and tools for management and content retrieval*
  * `Fetch`: *Tool to fetch a high-level object (resolves chunking)*
  * `ICNDataRepository`: *Sets up a data repository*
  * `ICNForwarder`: *Sets up a forwarder*
  * `Mgmt`: *Tool to send a management command to a node*
  * `NFNForwarder`: *Sets up a NFN computation node*
  * `SimpleFetch`: *Tool to fetch a single content object (without chunking)*
* **`Layers`**: *Contains one packet per layer*
  * `ChunkLayer`: *Chunking layer*
  * `ICNLayer`: *CCN network layer*
      * `Content Store`: *CS data structure*
      * `ForwardingInformationBase`: *FIB data structure*
      * `PendingInterest Table`: *PIT data structure*
  * `LinkLayer`: *Link layer (face management)*
  * `NFNLayer`: *Computation (NFN) layer*
    * `NFNEvaluator`: *NFN execution engine*
    * `Parser`: *Parser for computation expressions*
  * `PacketEncodingLayer`: *Conversion between wire format packets and python objects*
  * `RepositoryLayer`: *Persistent data storage*
* **`Logger`**: *Logging helpers*
* **`Mgmt`**: *Management interface*
* **`Packets`**: *Wire format helpers*
* **`Processes`**: *Communication between layers*
* **`ProgramLibs`**: Layer compositions *(See "Executable" package for starter scripts)*
  * `Fetch`: *Simple fetch tool*
  * `ICNDataRepository`: *CCN repository*
  * `ICNForwarder`: *CCN forwarder*
  * `NFNForwarder`: *NFN forwarder*
* **`Routing`**: *TBD (routing solution should go in here)*