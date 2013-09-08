class BaseWriter(object):
    """Base writer interface to be extended by other writers"""

    def __init__(self, pairs, *args, **kwargs):
        self.pairs = pairs

    def get_output_filename(self, infile):
        raise NotImplementedError

    def write(self, fp):
        raise NotImplementedError
