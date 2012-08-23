import array
import bisect
import sys
import wave

import numpy as np

from filters import absorb_short_notes, durations_in_seconds
from writers import midi


#TODO? make note durations fit 1/16th (or 1/(2^k)th for some k) of a note


# Size (in samples) of window partition used to compute DFT
WINDOW_SIZE = 2 ** 12

# Treshold for amplitude of largest frequency in DFT output to register as
# a note
SILENCE_TRESHOLD = 10000

# Filter functions to be applied to the output of waveform analysis
FILTERS = [absorb_short_notes, durations_in_seconds]

# Used for 'clamping' frequency to a standard MIDI frequency
TABLE = [
    0.0, 8.66, 9.18, 9.72, 10.30, 10.91, 11.56, 12.25, 12.98, 13.75, 14.57,
    15.43, 16.35, 17.32, 18.35, 19.45, 20.60, 21.83, 23.12, 24.50, 25.96,
    27.50, 29.14, 30.87, 32.70, 34.65, 36.71, 38.89, 41.20, 43.65, 46.25,
    49.00, 51.91, 55.00, 58.27, 61.74, 65.41, 69.30, 73.42, 77.78, 82.41,
    87.31, 92.50, 98.00, 103.83, 110.00, 116.54, 123.47, 130.81, 138.59,
    146.83, 155.56, 164.81, 174.61, 185.00, 196.00, 207.65, 220.00, 233.08,
    246.94, 261.63, 277.18, 293.66, 311.13, 329.63, 349.23, 369.99, 392.00,
    415.30, 440.00, 466.16, 493.88, 523.25, 554.37, 587.33, 622.25, 659.26,
    698.46, 739.99, 783.99, 830.61, 880.00, 932.33, 987.77, 1046.50,
    1108.73, 1174.66, 1244.51, 1318.51, 1396.91, 1479.98, 1567.98, 1661.22,
    1760.00, 1864.66, 1975.53, 2093.00, 2217.46, 2349.32, 2489.02, 2637.02,
    2793.83, 2959.96, 3135.96, 3322.44, 3520.00, 3729.31, 3951.07, 4186.01,
    4434.92, 4698.64, 4978.03, 5274.04, 5587.65, 5919.91, 6271.93, 6644.88,
    7040.00, 7458.62, 7902.13, 8372.02, 8869.84, 9397.27, 9956.06, 10548.08,
    11175.30, 11839.82, 12543.85, float(sys.maxint)]


def clamp(freq):
    """Round the frequency to the nearest MIDI note"""
    i = bisect.bisect(TABLE, freq)
    left, right = TABLE[i - 1], TABLE[i]
    if (freq - left) < (right - freq):
        return i - 1
    else:
        return i


def gather_notes(seq):
    """Given a sequence of MIDI note numbers, output a list of pairs (n, d)
    where n is the MIDI note and d is the duration of that note (i.e. number
    of consecutive repetition of that note).

    Example:
        gather_notes([53, 92, 92, 92, 96, 96]) --> [(53,1), (92,3), (96,2)]
    """

    pairs = []
    sq = seq[:]
    while len(sq) > 0:
        note = sq[0]
        xs = map(lambda x: x == note, sq)
        try:
            duration = xs.index(False)
        except ValueError:
            duration = len(xs)
        pairs.append((note, duration))
        sq = sq[duration:]

    return pairs


def filter_output(pairs, filters, params=None):
    """Apply filter functions in FILTERS successively to the list of pairs"""
    result = pairs
    for fn in filters:
        result = fn(result, params)
    return result


def read_wave(infile):
    """Given a WAV file as input, returns a list of pairs (note, duration)
    suitable for use by a writer.
    """

    w = wave.open(infile, 'r')

    nchannels, sampwidth, framerate, nframes, comptype, _ = w.getparams()

    if nchannels != 1:
        print('Only mono files are supported at the moment')
        sys.exit(1)
    elif sampwidth != 2:
        print('Only 16-bit files are supported at the moment')
        sys.exit(1)
    elif not (44000 <= framerate <= 44100):
        print('Only 44kHz files are supported at the moment')
        sys.exit(1)
    elif comptype != 'NONE':
        print('Only uncompressed files are supported')
        sys.exit(1)

    raw_data = w.readframes(nframes)
    a = array.array('h', raw_data)
    w.close()

    freqs = []
    window_size = WINDOW_SIZE

    # frequencies axis
    xs = np.fft.fftfreq(window_size, 1.0 / framerate)[:window_size / 4]
    for i in range(nframes / window_size):
        window = a[i * window_size: (i + 1) * window_size]
        if len(window) < window_size:
            break

        # amplitude axis
        ys = abs(np.fft.fft(window)[:window_size / 4])

        if ys.max() < SILENCE_TRESHOLD:
            freq = 0.0
        else:
            freq = xs[ys.argmax()]
        freqs.append(freq)

    clamped_freqs = map(clamp, freqs)
    pairs = gather_notes(clamped_freqs)
    return filter_output(pairs, FILTERS, locals())


if __name__ == '__main__':
    try:
        infile = sys.argv[1]
    except IndexError:
        print('No input file')
        sys.exit(1)
    output = read_wave(infile)
    """
    m = midi.Midi(output)
    m.write(infile.replace('.wav', '.mid'))
    """