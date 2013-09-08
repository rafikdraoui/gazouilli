import os.path

from .base import BaseWriter


class Floppy(BaseWriter):
    """Writer for Flopkestra bytecode file format"""

    def __init__(self, pairs, song_name='song'):
        """Build a representation of the music data from a list of pairs
        (n, d) where n is a MIDI note and d a duration in seconds.
        """
        self.song_name = song_name
        self.track = [(n, int(d * 1000)) for n, d in pairs]

    def get_output_filename(self, infile):
        name, ext = os.path.splitext(infile)
        return name + '.floppy'

    def write(self, fp):
        fp.write('const byte {}[] PROGMEM = {{\n'.format(self.song_name))

        # write length of song
        fp.write(to_hex(len(self.track) * 3 + 5))

        # write number of tracks
        fp.write(', 0x1, ')

        # write length of track
        fp.write(to_hex(len(self.track)))

        # write notes and durations
        for note, duration in self.track:
            fp.write(', {}, {}'.format(hex(note), to_hex(duration)))
        fp.write('\n}\n')


def to_hex(value):
    """Convert the given integer value into a two byte string
    representation suitable for flopkestra bytecode file format.
    """
    high_byte = hex((0xFF00 & value) >> 8)
    low_byte = hex(0xFF & value)
    return '{}, {}'.format(high_byte, low_byte)
