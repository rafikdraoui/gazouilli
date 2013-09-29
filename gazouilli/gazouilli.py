import array
import sys
import wave

import numpy as np

from .utils import clamp, collect_consecutive_values


class GazouilliException(Exception):
    pass


class Gazouilli(object):

    def __init__(self, writer, filters=None, stream=sys.stdout,
                 writer_options=None, filters_kwargs=None):
        self.writer = writer
        self.filters = filters or []
        self.stream = stream
        self.writer_options = writer_options or {}
        self.filters_kwargs = filters_kwargs or {}

    def filter_pairs(self, pairs):
        for fn in self.filters:
            pairs = fn(pairs, **self.filter_kwargs)
        return pairs

    def convert(self, pairs, filtered=False):
        if filtered:
            pairs = self.filter_pairs(pairs)

        w = self.writer(pairs, **self.writer_options)
        w.write(self.stream)


class WaveReader(object):

    def __init__(self, window_size=2**12, silence_threshold=10000):
        """
        `window_size` is the size (in number of of samples) of the window
        partitions used to compute the DFT.

        `silence_threshold` is the minimum value that the amplitude of the largest
        frequency in DFT output for a window must have in order to register as a
        note.
        """
        self.window_size = window_size
        self.silence_threshold = silence_threshold

    def read(self, infile):
        """Given the name of a WAV file as input, returns a list of pairs
        (note, duration) where `note` is a the number of a MIDI note and
        `duration` is the duration of that note in seconds.
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
        data = array.array('h', raw_data)
        w.close()

        freqs = self.get_frequencies(data, nframes, framerate)

        seconds_per_window = (1.0 / framerate) * self.window_size
        pairs = self.prepare_freqs(freqs, seconds_per_window)

        return pairs

    def get_frequencies(self, data, nframes, framerate):
        window_size = self.window_size
        freqs = []

        # frequencies axis
        xs = np.fft.fftfreq(window_size, 1.0 / framerate)[:window_size / 4]

        for i in range(nframes / window_size):
            low, high = i * window_size, (i + 1) * window_size
            window = data[low:high]

            if len(window) < window_size:
                break

            # amplitude axis
            ys = abs(np.fft.fft(window)[:window_size / 4])

            if ys.max() < self.silence_threshold:
                freq = 0.0
            else:
                freq = xs[ys.argmax()]

            freqs.append(freq)

    def prepare_freqs(self, freqs, seconds_per_window):
        """Convert the sequence of raw frequencies `freqs` to a list of
        (note, duration) pairs.
        """

        # Convert frequencies to the nearest MIDI note number
        clamped_freqs = map(clamp, freqs)

        # Gather windows having the same note value together to get a list of
        # (note, duration) pairs
        pairs = collect_consecutive_values(clamped_freqs)

        # Convert durations in number of windows to durations in seconds
        pairs = [(n, d * seconds_per_window) for n, d in pairs]

        return pairs
