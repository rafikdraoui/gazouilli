import argparse
import array
import json
import sys
import wave

import numpy as np

from . import filters, writers
from .utils import clamp, collect_consecutive_values


# Names of valid writers
VALID_WRITERS = [w.lower() for w in writers.__all__]


class GazouilliException(Exception):
    pass


def read_wave(infile, window_size=2**12, silence_threshold=10000):
    """Given the name of a WAV file as input, returns a list of pairs
    (note, duration) where `note` is a the number of a MIDI note and
    `duration` is the duration of that note in seconds.

    `window_size` is the size (in number of of samples) of the window
    partitions used to compute the DFT.

    `silence_threshold` is the minimum value that the amplitude of the largest
    frequency in DFT output for a window must have in order to register as a
    note.
    """

    try:
        w = wave.open(infile, 'r')
    except (IOError, wave.Error) as e:
        raise GazouilliException(
            'Cannot read WAV file.\nGot error: "{}"'.format(e))

    nchannels, sampwidth, framerate, nframes, comptype, _ = w.getparams()

    if nchannels != 1:
        raise GazouilliException('Only mono files are supported at the moment')
    if sampwidth != 2:
        raise GazouilliException('Only 16-bit files are supported at the moment')
    if not (44000 <= framerate <= 44100):
        raise GazouilliException('Only 44kHz files are supported at the moment')
    if comptype != 'NONE':
        raise GazouilliException('Only uncompressed files are supported')

    raw_data = w.readframes(nframes)
    a = array.array('h', raw_data)
    w.close()

    freqs = []

    # frequencies axis
    xs = np.fft.fftfreq(window_size, 1.0 / framerate)[:window_size / 4]

    for i in range(nframes / window_size):
        window = a[i * window_size: (i + 1) * window_size]
        if len(window) < window_size:
            break

        # amplitude axis
        ys = abs(np.fft.fft(window)[:window_size / 4])

        if ys.max() < silence_threshold:
            freq = 0.0
        else:
            freq = xs[ys.argmax()]
        freqs.append(freq)

    # Convert frequencies to the nearest MIDI note number
    clamped_freqs = map(clamp, freqs)

    # Gather windows having the same note value together to get a list of
    # (note, duration) pairs
    pairs = collect_consecutive_values(clamped_freqs)

    # Convert durations in number of windows to durations in seconds
    seconds_per_window = (1.0 / framerate) * window_size
    pairs = [(n, d * seconds_per_window) for n, d in pairs]

    return pairs


def convert(infile, output_format, filters_to_use, outfile=None, stdout=False):
    """Convert input file `infile` to the format given by `output_format`
    using filters in `filters_to_use`.

    If `stdout` is True, the output of the writer is written to stdout,
    otherwise it is written to the file `outfile`. If `outfile` is not given
    and the writer has an implementation of the `get_output_filename` method,
    then the result of this method is used as an output filename.
    """

    pairs = read_wave(infile)

    for fn in filters_to_use:
        pairs = fn(pairs)

    writer_class = getattr(writers, output_format.capitalize())
    writer = writer_class(pairs)

    if stdout:
        fp = sys.stdout
    else:
        if outfile is None:
            try:
                outfile = writer_class.get_output_filename(infile)
            except NotImplementedError:
                raise GazouilliException(
                    'Must specify at least one of `output` or `stdout` option '
                    'with this writer'
                )
        fp = open(outfile, 'wb')

    writer.write(fp)
    fp.close()


def _get_arguments():
    """Create an arguments parser and return the parsed arguments from
    sys.argv"""

    parser = argparse.ArgumentParser(
        description='Convert a wave audio file to other formats.')
    parser.add_argument('infile', help='The input wave file.')
    parser.add_argument(
        '-c', '--conf',
        help='Configuration file containing the options to be used (in '
             'json format). If this option is used, any other option given '
             'on the command line will be ignored.'
    )
    parser.add_argument(
        '-w', '--writer', choices=VALID_WRITERS,
        help='The writer to use for the output.'
    )
    parser.add_argument(
        '-f', '--filters', nargs='*', metavar='FILTER', default=[],
        choices=filters.__all__,
        help='Filters to be used, in the order of their application, separated '
             'by whitespace. Note that if this option directly precedes the '
             '`infile` argument, the latter will be wrongly considered to be a '
             'filter. To correct this problem, the filters need to be separated '
             'from the `infile` argument with other options, or with `--` if '
             'this is the last option used.'
    )
    parser.add_argument(
        '-o', '--output', metavar='OUTFILE',
        help='The output file. If both the `outfile` and `stdout` options are '
             'omitted, then the output filename will be the same as the input '
             'file with the .wav ending changed to an appropriate extension. '
             'Cannot be used with `stdout`.'
    )
    parser.add_argument(
        '--stdout', action='store_true',
        help='Write the output to stdout. Not all writers can write to stdout '
             'Cannot be used with `output`.'
    )

    return parser.parse_args()


def _handle_error(*messages):
    """Print each message in the `messages` sequence on its own line  and
    exit the program with exit code 1.
    """
    sys.stderr.write('Error: ' + '\n'.join(messages) + '\n')
    sys.exit(1)


if __name__ == '__main__':

    args = _get_arguments()

    if args.conf:
        try:
            with open(args.conf, 'r') as f:
                conf = json.load(f)
        except (IOError, ValueError) as e:
            _handle_error('Cannot read configuration file',
                          'Got error: "{}"'.format(e))

        filters_names = conf.get('filters', [])
        filters_to_use = [getattr(filters, fltr) for fltr in filters_names]

        writer = conf.get('writer')
        output = conf.get('output')
        stdout = conf.get('stdout', False)

    else:
        filters_to_use = [getattr(filters, fltr) for fltr in args.filters]
        writer = args.writer
        output = args.output
        stdout = args.stdout

    if not writer or writer not in VALID_WRITERS:
        _handle_error('Invalid writer specified. Valid choices are:',
                      ', '.join(VALID_WRITERS))

    if stdout and output:
        _handle_error('Cannot specify both `outfile` and `stdout` options')

    try:
        convert(args.infile, writer, filters_to_use, output, stdout)
    except GazouilliException as e:
        _handle_error(e.message)
