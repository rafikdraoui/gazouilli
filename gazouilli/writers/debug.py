from pprint import PrettyPrinter

from .base import BaseWriter


class Debug(BaseWriter):
    """Writer that output a pretty-printed representation of the input pairs"""

    def write(self, fp):
        pp = PrettyPrinter(stream=fp)
        pp.pprint(self.pairs)
