== how to run the repo demo

Features:
- write and read to local repo
- demonstrate the use of FLIC manifest
- demonstrate the use for NFN results

How to start:
```
cd PiCN/examples
mkdir repo
../PiCn/Executable/ICNDataRepository.py ./repo /the/prefix 9876 &

./write_read.py
./write_read-flic.py
./write_read-flic-nfn.py
```
