# -*- coding: utf-8

import array
import io
import os.path
import struct

from .base import BaseWriter


class Midi(BaseWriter):
    """Writer for MIDI file format"""

    def __init__(self, pairs, division=96, tempo=500000, velocity=127,
                 normalize_note_length=False):
        """Build a representation of the MIDI data from a list of pairs
        (n, d) where n is a MIDI note and d a duration in seconds.

        `division` is the number of ticks making up a quarter-note.

        `tempo` is the time (in µs) per quarter-note.

        `velocity` is a number from 0 to 127 that, in our case, can be thought
        of as the volume for the song.

        If `normalize_note_length` is True, then each note duration will be
        rounded to the nearest multiple of a sixteenth note.
        """
        self.track = []
        self.division = division
        self.tempo = tempo
        self.velocity = velocity

        note_on = 0x90
        note_off = 0x80
        cleaned_pairs = strip_trailing_silence(pairs)

        for note, duration in cleaned_pairs:
            length_in_ticks = int(duration * self.division * (1e6 / self.tempo))
            if normalize_note_length:
                length_in_ticks = round_to_closest_sixteenth_note(
                    length_in_ticks, self.division)
            self.track.append((0, note_on, note))
            self.track.append((length_in_ticks, note_off, note))

    def write(self, fp):

        # 1. Write track to temporary buffer. This is needed since we need to
        #    know the length (in bytes) of the track to write the track header
        #    section, and we cannot know it until we processed all the note
        #    events.
        buf = io.StringIO()

        # set tempo event: FF5103 tttttt
        # tttttt is the tempo (i.e. time in µs per quarter-note)
        buf.write('\x00')
        buf.write('\xff\x51\x03')
        buf.write(get_bytes_for_tempo(self.tempo))

        # note events
        running_time = 0
        for time, event, note in self.track:
            if note == 0:  # silence
                running_time += time
                continue

            buf.write(var_len(time + running_time))
            buf.write(struct.pack('>BBB', event, note, self.velocity))

            running_time = 0

        # end of track event: FF 2F 00
        buf.write('\x00\xff\x2f\x00')

        # 2. Now write the MIDI formatted output to stream

        # header
        #  = <type> <header length> <format> <numtrack> <division>
        fp.write('MThd')
        fp.write(struct.pack('>iHHH', 6, 0, 1, self.division))

        # track
        fp.write('MTrk')
        fp.write(struct.pack('>i', buf.len))
        fp.write(buf.getvalue())

        buf.close()

    @staticmethod
    def get_output_filename(infile):
        name, ext = os.path.splitext(infile)
        return name + '.mid'


def round_to_closest_sixteenth_note(length_in_ticks, division):
    t = division / 4  # number of ticks per 1/16th note

    num_sixteenth_notes = length_in_ticks / t
    remainder = length_in_ticks % t

    if remainder > t / 2:
        # round to next multiple of `t`
        num_sixteenth_notes += 1

    return num_sixteenth_notes * t


def strip_trailing_silence(pairs):
    end = len(pairs)
    while end and pairs[end-1][0] == 0:
        end -= 1

    return pairs[:end]


def get_bytes_for_tempo(tempo):
    """Convert the given integer value into a three byte hex representation"""
    high_byte = (0xFF0000 & tempo) >> 16
    mid_byte = (0xFF00 & tempo) >> 8
    low_byte = 0xFF & tempo

    return struct.pack('>BBB', high_byte, mid_byte, low_byte)


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
