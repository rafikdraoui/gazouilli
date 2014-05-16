from __future__ import absolute_import

import json
import os.path

from .base import BaseWriter


class Json(BaseWriter):
    """Writer that output a JSON representation of the input pairs"""

    def write(self, fp):
        json.dump(self.pairs, fp)

    @staticmethod
    def get_output_filename(infile):
        name, ext = os.path.splitext(infile)
        return name + '.json'
