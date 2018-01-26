"""A Simple File System Repository"""


import os.path

from PiCN.Layers.RepositoryLayer.Repository import BaseRepository
from PiCN.Packets import Content, Name
from PiCN.Logger import Logger


class SimpleFileSystemRepository(BaseRepository):
    """A Simple File System Repository"""

    def __init__(self, foldername: str, prefix: Name, logger: Logger=None):
        super().__init__()
        self._foldername: str = foldername
        self._safepath = safepath = os.path.abspath(self._foldername)
        self._prefix = prefix
        self.logger = logger


    def is_content_available(self, icnname: Name) -> bool:
        if not icnname.to_string().startswith(self._prefix.to_string()):
            return False
        filename = icnname.components[-1]
        filename_abs = self._foldername + "/" + filename
        filepath = os.path.abspath(filename_abs)
        if os.path.commonprefix([filepath, self._safepath]) != self._safepath:  # prevent directory traversal
            return False
        if os.path.isfile(filename_abs):
            return True
        return False


    def get_content(self, icnname: Name) -> Content:
        if not icnname.to_string().startswith(self._prefix.to_string()):
            return None
        try:
            filename = icnname.components[-1]
            filename_abs = self._foldername + "/" + filename
            filepath = os.path.abspath(filename_abs)
            if os.path.commonprefix([filepath, self._safepath]) != self._safepath: #prevent directory traversal
                return None
            with open(filename_abs, 'r') as content_file:
                content = content_file.read()
            return Content(icnname, content)
        except:
            return None

    def set_content(self, icnname: Name, chunk: bytes):
        try:
            os.stat( self._foldername)
        except:
            os.mkdir( self._foldername)
        with open( self._foldername + icnname.to_string(), 'w+') as f:
            f.write(chunk)

# eof
