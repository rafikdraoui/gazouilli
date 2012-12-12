"""
Modules that implement writing output from gazouilli into another format.

Each writer must have a `file_extension` attribute (a string) and a `write`
method taking a single argument `outfile`, the name of the file in which the
output is written.
"""

from .floppy import Floppy
from .midi import Midi

__all__ = ['Floppy', 'Midi']
