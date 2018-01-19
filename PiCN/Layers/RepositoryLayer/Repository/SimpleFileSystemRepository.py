"""A Simple File System Repository"""

'''
chunks are stored in files named as follows:
  base64(icnname) + '.' + sha256(chunk)
'''

import base64
import binascii
import fnmatch
import hashlib
import os

from PiCN.Layers.RepositoryLayer.Repository import BaseRepository
from PiCN.Packets import Content, Name


class SimpleFileSystemRepository(BaseRepository):
    """A Simple File System Repository"""

    def __init__(self, foldername: str, prefix: Name):
        super().__init__()
        self._foldername: str = foldername
        self._safepath = safepath = os.path.abspath(self._foldername)
        self._prefix = prefix

    def _name2pattern(self, icnname: Name, digest=None) -> str:
        fnpattern = base64.b64encode(icnname.to_string().encode('ascii'))
        if digest:
            fnpattern += b'.' + binascii.hexlify(digest)
        else:
            fnpattern += b'.*'
        return fnpattern.decode('ascii')

    def is_content_available(self, icnname: Name, digest=None) -> bool:
        fnpattern = self._name2pattern(icnname, digest)
        for file in os.listdir(self._safepath):
            if fnmatch.fnmatch(file, fnpattern):
                return True
        return False

    def get_content(self, icnname: Name, digest=None) -> Content:
        if not self._prefix.is_prefix_of(icnname):
            return None
        fnpattern = self._name2pattern(icnname, digest)
        for fn in os.listdir(self._safepath):
            if fnmatch.fnmatch(fn, fnpattern):
                fn = os.path.join(self._safepath, fn)
                with open(fn, 'rb') as f:
                    chunk = f.read()
                    return Content(icnname, chunk)
        return None

    def set_content(self, icnname: Name, chunk: bytes):
        if not self._prefix.is_prefix_of(icnname):
            raise IOError
        h = hashlib.sha256()
        h.update(chunk)
        fn = self._name2pattern(icnname, h.digest())
        fn = os.path.join(self._safepath, fn)
        if os.path.isfile(fn):
            raise IOError
        with open(fn, "wb") as f:
            f.write(chunk)

# eof
