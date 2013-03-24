import argparse
import array
import bisect
import json
import sys
import wave

import numpy as np

import filters
import writers


# Names of valid writers
VALID_WRITERS = [w.lower() for w in writers.__all__]

# Size (in samples) of window partition used to compute DFT
WINDOW_SIZE = 2 ** 12

# Threshold for amplitude of largest frequency in DFT output to register as
# a note
SILENCE_TRESHOLD = 10000

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
        xs = [x == note for x in sq]
        try:
            duration = xs.index(False)
        except ValueError:
            duration = len(xs)
        pairs.append((note, duration))
        sq = sq[duration:]

    return pairs


def filter_output(pairs, filters_to_use, params=None):
    """Apply filter functions in `filters_to_use` successively to the list of
    pairs.
    """
    result = pairs
    for fn in filters_to_use:
        result = fn(result, params)
    return result


def read_wave(infile, filters_to_use):
    """Given the name of a WAV file as input, returns a list of pairs
    (note, duration) filtered by the filters in the sequence `filters_to_use`.
    The output should be suitable to be used as the argument of the
    constructor for a writer object.
    """

    w = wave.open(infile, 'r')

    nchannels, sampwidth, framerate, nframes, comptype, _ = w.getparams()

    if nchannels != 1:
        _handle_error('Only mono files are supported at the moment')
    if sampwidth != 2:
        _handle_error('Only 16-bit files are supported at the moment')
    if not (44000 <= framerate <= 44100):
        _handle_error('Only 44kHz files are supported at the moment')
    if comptype != 'NONE':
        _handle_error('Only uncompressed files are supported')

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
    return filter_output(pairs, filters_to_use, locals())


def convert(infile, output_format, filters_to_use, outfile=None):
    """Convert input file `infile` to the format given by `output_format`
    using filters in `filters_to_use`, writing the result to the file
    `outfile`. If the output file is not given, it defaults to the name of the
    input file with the .wav extension replaced by an appropriate extension
    for `output_format`.

    The input file name must have a '.wav' extension.
    """

    assert infile.endswith('.wav'), 'The input file must have a .wav extension'

    pairs = read_wave(infile, filters_to_use)
    writer = getattr(writers, output_format.capitalize())(pairs)
    if not outfile:
        outfile = infile.replace('.wav', writer.file_extension)
    writer.write(outfile)


def _get_arguments():
    """Create an arguments parser and return the parsed arguments from
    sys.argv"""

    parser = argparse.ArgumentParser(
        description='Convert a wave audio file to other formats.')
    parser.add_argument(
        'infile', help='The input wave file. Must end with a .wav extension')
    parser.add_argument(
        '-c', '--conf',
        help='Configuration file containing the options to be used (in '
             'json format). If this option is used, any other option given '
             'on the command line will be ignored.')
    parser.add_argument(
        '-w', '--writer', choices=VALID_WRITERS,
        help='The writer to use for the output.')
    parser.add_argument(
        '-f', '--filters', nargs='*', metavar='FILTER', default=[],
        choices=filters.__all__,
        help='Filters to be used, separated by whitespace. Note that if this '
             'option directly precedes the `infile` argument, the latter '
             'will be wrongly considered to be a filter. To correct this '
             'problem, the filters need to be separated from the `infile` '
             'argument with other options, or with `--` if this is the last '
             'option used.')
    parser.add_argument(
        '-o', '--output', metavar='OUTFILE',
        help='The output file. By default it has the same name as the input '
             'file with the .wav ending changed to an appropriate extension.')

    return parser.parse_args()


def _handle_error(*messages):
    """Print each message in the `messages` sequence on its own line  and
    exit the program with exit code 1.
    """
    sys.stderr.write('\n'.join(messages) + '\n')
    sys.exit(1)


if __name__ == '__main__':

    args = _get_arguments()

    if args.conf:
        try:
            with open(args.conf, 'r') as f:
                conf = json.load(f)
        except IOError:
            _handle_error('Cannot open configuration file')
        except ValueError as e:
            _handle_error('Cannot parse configuration file',
                          'Got error: "{}"'.format(e))

        filters_to_use = []
        for fltr in conf.get('filters', []):
            filters_to_use.append(getattr(filters, fltr))

        writer = conf.get('writer')
        if not writer or writer not in VALID_WRITERS:
            _handle_error('Invalid writer specified. Valid choices are:',
                          ', '.join(VALID_WRITERS))

        output = conf.get('output')

    else:
        filters_to_use = [getattr(filters, fltr) for fltr in args.filters]
        writer = args.writer
        output = args.output

    convert(args.infile, writer, filters_to_use, output)
