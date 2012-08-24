""" Writer for Flopkestra bytecode file format"""


class Floppy(object):

    def __init__(self, pairs):
        """ Build a representation of the music data from a list of pairs
        (n, d) where n is a MIDI note and d a duration in seconds.
        """
        self.track = map(lambda (n, d): (n, int(d * 1000)), pairs)

    def _to_hex(self, value):
        """ Convert the given integer value into a two byte string
        representation suitable for flopkestra bytecode file format.
        """
        high_byte = hex((0xFF00 & value) >> 8)
        low_byte = hex(0xFF & value)
        return '%s, %s' % (high_byte, low_byte)

    def write(self, outfile):
        """ Write itself to a flopkestra bytecode file in the file specified
        by outfile.
        """
        name = outfile.replace('.flb', '')
        with open(outfile, 'wb') as out:
            out.write('const byte %s[] PROGMEM = {\n' % name)

            # write length of song
            out.write(self._to_hex(len(self.track) * 3 + 5))

            # write number of tracks
            out.write(', 0x1, ')

            #write length of track
            out.write(self._to_hex(len(self.track)))

            # write notes and durations
            for note, duration in self.track:
                out.write(', %s, %s' % (hex(note), self._to_hex(duration)))
            out.write('\n}\n')