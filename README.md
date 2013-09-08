# gazouilli

This converts a WAV file recording into another format (MIDI, [flopkestra][]
bytecode, etc.)

## How does it work?

The input is a WAV audio recording. It is partitioned into windows (by
default, each window is 2^12 samples long, about 0.09s for a 44kHz sample
rate).  The [Discrete Fourier Transform][DFT] is applied to each window to
determine which frequency is dominant in this window. Each of these
frequencies are rounded to the nearest frequency that corresponds to
a standard MIDI note.

From these, a list of pairs `(n, d)` is created, where `n` is the number of
the MIDI note corresponding to the frequency and `d` is the duration of that
note in numbers of windows.

### Filters

The stream of pairs `(note, duration)` created by the previous step can be
transformed by filters. For example, one might want to weed out all notes that
have a too short duration, or bump all the note one octave up, or else to get
the duration of the notes in seconds instead of in number of windows.

### Writers

The filtered output is then given to one or more *writers* to be converted
into another format. At the moment, there are writers for MIDI files,
flopkestra bytecode and JSON.

## Dependencies

The only external dependency is [numpy][], which is used for the discrete
Fourier transform computations.

## About

This was built by [Rafik Draoui][] to make his floppy drive
orchestra play tunes he has in his head without having to figure out how to
write them down in MIDI or flopkestra bytecode by hand.


[flopkestra]: https://github.com/rafikdraoui/flopkestra
[DFT]: https://en.wikipedia.org/wiki/Discrete_Fourier_transform
[numpy]: http://www.numpy.org/
[Rafik Draoui]: http://www.rafik.ca
