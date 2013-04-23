"""Writer for Flopkestra bytecode file format"""


def to_hex(value):
    """Convert the given integer value into a two byte string
    representation suitable for flopkestra bytecode file format.
    """
    high_byte = hex((0xFF00 & value) >> 8)
    low_byte = hex(0xFF & value)
    return '{}, {}'.format(high_byte, low_byte)


class Floppy(object):

    file_extension = '.flb'

    def __init__(self, pairs):
        """Build a representation of the music data from a list of pairs
        (n, d) where n is a MIDI note and d a duration in seconds.
        """
        self.track = [(n, int(d * 1000)) for n, d in pairs]

    def write(self, outfile):
        """Write itself to a flopkestra bytecode file in the file specified
        by outfile.
        """
        name = outfile.replace('.flb', '')
        with open(outfile, 'wb') as out:
            out.write('const byte {}[] PROGMEM = {{\n'.format(name))

            # write length of song
            out.write(to_hex(len(self.track) * 3 + 5))

            # write number of tracks
            out.write(', 0x1, ')

            # write length of track
            out.write(to_hex(len(self.track)))

            # write notes and durations
            for note, duration in self.track:
                out.write(', {}, {}'.format(hex(note), to_hex(duration)))
            out.write('\n}\n')
