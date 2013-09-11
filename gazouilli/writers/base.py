class BaseWriter(object):
    """Base writer interface to be extended by other writers"""

    def __init__(self, pairs, *args, **kwargs):
        self.pairs = pairs

    def write(self, fp):
        raise NotImplementedError

    @staticmethod
    def get_output_filename(infile):
        raise NotImplementedError
