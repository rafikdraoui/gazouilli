import json
import os.path

from .base import BaseWriter


class Json(BaseWriter):
    """Writer that output a JSON representation of the input pairs"""

    def get_output_filename(self, infile):
        name, ext = os.path.splitext(infile)
        return name + '.json'

    def write(self, fp):
        json.dump(self.pairs, fp)
