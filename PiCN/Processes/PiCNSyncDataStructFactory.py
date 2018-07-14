"""Sync Datastruct Factory for PICN to create synced Datastructs such as PIT, FIB, CS"""

from multiprocessing.managers import BaseManager


class PiCNSyncDataStructFactory(object):
    """Sync Datastruct Factory for PICN to create synced Datastructs such as PIT, FIB, CS"""

    def __init__(self):
        self.manager = None
        self.names = []
        pass

    def register(self, name: str, data_struct):
        """register a new data_struct to the manager
        :param name: name of the datastruct under which it should be callable
        :param data_struct: data_structure to be added to the
        """
        if name in self.names:
            return
        BaseManager.register(name, data_struct)
        self.names.append(name)

    def create_manager(self):
        """create a manager. call is after all data structs are registered"""
        self.manager = BaseManager()
        self.manager.start()

    def get_manager(self) -> BaseManager:
        """get or create and get a Manager
        :return: the Manager to create synced datastructures
        """
        if self.manager is None:
            self.create_manager()
        return self.manager
