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
from PiCN.Logger import Logger, NullLogger


class SimpleFileSystemRepository(BaseRepository):
    """A Simple File System Repository"""

    def __init__(self, foldername: str, prefix: Name, logger: Logger=None):
        super().__init__()
        self._foldername: str = foldername
        self._safepath = safepath = os.path.abspath(self._foldername)
        self._prefix = prefix
        self.logger = logger if logger else NullLogger()

    def _name2pattern(self, icnname: Name, digest=None) -> str:
        fnpattern = icnname.components_to_string().encode('ascii')
        fnpattern = base64.b64encode(fnpattern)
        if digest:
            fnpattern += b'.' + binascii.hexlify(digest)
        else:
            fnpattern += b'.*'
        return fnpattern.decode('ascii')

    def is_content_available(self, icnname: Name) -> bool:
        self.logger.info("availability of %s" % str(icnname))
        fnpattern = self._name2pattern(icnname, icnname.digest)
        for file in os.listdir(self._safepath):
            if fnmatch.fnmatch(file, fnpattern):
                self.logger.info("  content exists")
                return True
        self.logger.info("  no such content")
        return False

    def get_content(self, icnname: Name) -> Content:
        self.logger.info("fetch content for %s" % str(icnname))
        if not self._prefix.is_prefix_of(icnname):
            self.logger.info("  no such content, prefix mismatch")
            return None
        fnpattern = self._name2pattern(icnname, icnname.digest)
        for fn in os.listdir(self._safepath):
            if fnmatch.fnmatch(fn, fnpattern):
                fn = os.path.join(self._safepath, fn)
                with open(fn, 'rb') as f:
                    chunk = f.read()
                    self.logger.info("  found %d bytes" % len(chunk))
                    return Content(icnname, chunk)
        self.logger.info("  no such content")
        return None

    def set_content(self, icnname: Name, chunk: bytes):
        self.logger.info("set content (%d bytes) for %s" % \
                        (len(chunk), str(icnname)))
        if not self._prefix.is_prefix_of(icnname):
            self.logger.info("  not stored, prefix mismatch")
            raise IOError
        h = hashlib.sha256()
        h.update(chunk)
        fn = self._name2pattern(icnname, h.digest())
        fn = os.path.join(self._safepath, fn)
        if os.path.isfile(fn):
            raise IOError
        with open(fn, "wb") as f:
            f.write(chunk)
        self.logger.info("  stored")

# eof
