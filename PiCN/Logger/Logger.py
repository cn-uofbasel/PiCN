"""PiCN Logger"""

import logging

class Logger(logging.Logger):
    """PiCN Logger"""

    def __init__(self, name, level):
        if __name__ == "__test__":
            level=255
        super().__init__(name, level)
        self.setLevel(level)
        formatter = logging.Formatter('%(asctime)s - %(name)s \t %(levelname)s: \t %(message)s')
        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        self.addHandler(ch)


class NullLogger(logging.Logger):

    def __init__(self):
        pass

    def info(self, s):
        pass

    def warning(self, s):
        pass
