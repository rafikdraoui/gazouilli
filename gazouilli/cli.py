import argparse
import json
import sys

from . import filters, writers
from .gazouilli import Gazouilli, GazouilliException, WaveReader


# Names of valid writers
VALID_WRITERS = [w.lower() for w in writers.__all__]


def convert(infile, output_format, filters_to_use, outfile=None, stdout=False):
    """Convert input file `infile` to the format given by `output_format`
    using filters in `filters_to_use`.

    If `stdout` is True, the output of the writer is written to stdout,
    otherwise it is written to the file `outfile`. If `outfile` is not given
    and the writer has an implementation of the `get_output_filename` method,
    then the result of this method is used as an output filename.
    """

    writer = getattr(writers, output_format.capitalize())

    if stdout:
        fp = sys.stdout
    else:
        if outfile is None:
            try:
                outfile = writer.get_output_filename(infile)
            except NotImplementedError:
                raise GazouilliException(
                    'Must specify at least one of `output` or `stdout` option '
                    'with this writer'
                )
        fp = open(outfile, 'wb')

    pairs = WaveReader().read(infile)
    gazouilli = Gazouilli(writer, filters=filters_to_use, stream=fp)
    gazouilli.convert(pairs, apply_filters=True)
    fp.close()


def get_arguments():
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


def handle_error(*messages):
    """Print each message in the `messages` sequence on its own line  and
    exit the program with exit code 1.
    """
    sys.stderr.write('Error: ' + '\n'.join(messages) + '\n')
    sys.exit(1)


def run():

    args = get_arguments()

    if args.conf:
        try:
            with open(args.conf, 'r') as f:
                conf = json.load(f)
        except (IOError, ValueError) as e:
            handle_error('Cannot read configuration file',
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

    if writer is None or writer not in VALID_WRITERS:
        handle_error('Invalid writer specified. Valid choices are:',
                     ', '.join(VALID_WRITERS))

    if stdout and output:
        handle_error('Cannot specify both `outfile` and `stdout` options')

    try:
        convert(args.infile, writer, filters_to_use, output, stdout)
    except GazouilliException as e:
        handle_error(e.message)
