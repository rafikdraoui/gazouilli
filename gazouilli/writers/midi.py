import array
import os.path
import struct
import StringIO

from .base import BaseWriter


NOTE_ON = 'on'
NOTE_OFF = 'off'


class Midi(BaseWriter):
    """Writer for MIDI file format"""

    def __init__(self, pairs, division=96):
        """Build a representation of the MIDI data from a list of pairs
        (n, d) where n is a MIDI note and d a duration in seconds.
        """
        self.track = []
        self.division = division
        for note, duration in pairs:
            length_in_ticks = int(duration * 2 * self.division)
            self.track.append((0, NOTE_ON, note))
            self.track.append((length_in_ticks, NOTE_OFF, note))

    def get_output_filename(self, infile):
        name, ext = os.path.splitext(infile)
        return name + '.mid'

    def write(self, fp):

        # 1. Write track to buffer
        buf = StringIO.StringIO()

        # set tempo event: FF5103 tttttt
        buf.write('\x00')
        buf.write('\xff\x51\x03')
        buf.write('\x07\xa1\x20')

        # note events
        running_time = 0
        for time, event, note in self.track:
            if note == 0:  # silence
                running_time += time
                continue
            buf.write(var_len(time + running_time))
            code = 0x90 if event == NOTE_ON else 0x80
            buf.write(struct.pack('>BBB', code, note, 127))
            running_time = 0

        # end of track event: FF 2F 00
        # TODO: adjust delta-time if final note is 0
        buf.write('\x00\xff\x2f\x00')

        # 2. Now write the MIDI formatted output to stream

        # header
        fp.write('MThd')
        fp.write(struct.pack('>iHHH', 6, 0, 1, self.division))

        # track
        fp.write('MTrk')
        fp.write(struct.pack('>i', buf.len))
        fp.write(buf.getvalue())

        buf.close()


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
