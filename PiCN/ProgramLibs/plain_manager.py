"""Minimal stand-in for multiprocessing.Manager used by repository storage.

Async ProgramLib path prefers plain in-process objects (ADR-004). Repository
classes still require a Manager-like API (``.dict()``, ``.Value``); this shim
satisfies that without starting a Manager process.
"""


class _PlainValue(object):
    def __init__(self, value):
        self.value = value


class PlainRepoManager(object):
    """Provide ``dict`` / ``Value`` like ``multiprocessing.Manager``."""

    def dict(self):
        return {}

    def Value(self, typ, value):
        return _PlainValue(value)

    def list(self):
        return []
