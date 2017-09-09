# Copyright (c) Moshe Zadka
# See LICENSE for details.
"""Main

For use as 'python -m ncolony ...'
"""
import sys

import gather

import ncolony
from ncolony import main

if __name__ != '__main__':
    raise ImportError("This module cannot be imported")

gather.run(
    commands=main.COMMANDS.collect(),
    version=ncolony.__version__,
    argv=sys.argv[1:],
    output=sys.stdout
)
