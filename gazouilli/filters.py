"""
Filters for output of wave form analysis.

The input for the filter functions should be a list of pairs (n, d) At first
`n` denotes the MIDI note number and `d` the duration in seconds, but the
filters can change the meaning of these, as long as the output is another list
of pairs (the functions should be composable with one another).
"""


__all__ = [
    'weed_out_short_notes',
    'absorb_short_notes',
    'convert_duration_to_integer',
]


def weed_out_short_notes(pairs, **kwargs):
    """Remove notes from pairs whose duration are smaller than the threshold"""
    duration_threshold = kwargs.get('duration_threshold', 0.25)
    return [(n, d) for (n, d) in pairs if d > duration_threshold]


# TODO: make this more pythonic?
def absorb_short_notes(pairs, **kwargs):
    """
    If a note with a short duration appears between two of the same notes,
    change the short note to the surrounding ones to make a continous long
    note. Otherwise the short note is removed.

    This avoids the effect of fluctuations in a note. However this has the
    effect of merging repeated notes separated by short silences (or rapid
    alternation of two notes) into a single long note.

    Example:
        >>> absorb_short_notes([(95, 2), (96, 1), (95, 8), (92, 6)], {})
        [(95, 11), (92, 6)]
    """

    duration_threshold = kwargs.get('duration_threshold', 0.25)

    result = []
    i = 0
    while i < len(pairs):
        pair = pairs[i]
        n, d = pair
        try:
            n1, d1 = pairs[i + 1]
            n2, d2 = pairs[i + 2]
        except IndexError:
            if d > duration_threshold:
                result.append(pair)
            i += 1
            continue

        if n == n2 and d1 < duration_threshold:
            new_pair = (n, d + d1 + d2)
            result.append(new_pair)
            i += 3
        else:
            if d > duration_threshold:
                result.append(pair)
            i += 1

    return result


def convert_duration_to_integer(pairs, **kwargs):
    ratio = kwargs.get('ratio', 16)

    return [(n, int(round(d * ratio))) for n, d in pairs]
