"""Writer for MIDI file format"""

import struct
import array
import StringIO


def var_len(value):
    """Return the variable length encoding of the input (integer) value
    as specified by the MIDI standard.
    """
    buf = value & 0x7f
    value >>= 7
    while value:
        buf <<= 8
        buf |= 0x80
        buf += value & 0x7f
        value >>= 7

    a = array.array('B')
    while True:
        a.append(buf & 0xFF)
        if buf & 0x80:
            buf >>= 8
        else:
            break

    return a.tostring()


class Midi(object):

    file_extension = '.mid'

    def __init__(self, tuples, division=96):
        """Build a representation of the MIDI data from a list of pairs
        (n, d) where n is a MIDI note and d a duration in seconds.
        """
        self.track = []
        self.division = division
        for note, duration in tuples:
            length_in_ticks = int(duration * 2 * self.division)
            self.track.append((0, 'note on', note))
            self.track.append((length_in_ticks, 'note off', note))

    def write(self, outfile):
        """Write itself to a valid MIDI file in the file specified by
        outfile.
        """

        # write track to buffer
        buf = StringIO.StringIO()

        # write set tempo event: FF5103 tttttt
        buf.write('\x00')
        buf.write('\xff\x51\x03')
        buf.write('\x07\xa1\x20')

        # write note events
        running_time = 0
        for time, event, note in self.track:
            if note == 0:  # silence
                running_time += time
                continue
            buf.write(var_len(time + running_time))
            code = 0x90 if event == 'note on' else 0x80
            buf.write(struct.pack('>BBB', code, note, 127))
            running_time = 0

        # write end of track event: FF 2F 00
        # TODO: adjust delta-time if final note is 0
        buf.write('\x00\xff\x2f\x00')

        with open(outfile, 'wb') as out:
            # write header
            out.write('MThd')
            out.write(struct.pack('>iHHH', 6, 0, 1, self.division))

            # write track
            out.write('MTrk')
            out.write(struct.pack('>i', buf.len))
            out.write(buf.getvalue())
        buf.close()
