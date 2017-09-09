# Copyright (c) Moshe Zadka
# See LICENSE for details.
"""Main

For use as 'python -m ncolony [reaper|ctl] ...'
"""
import os
import sys

import gather

import ncolony
from ncolony import main

if __name__ != '__main__':
    raise ImportError("This module cannot be imported")

if os.path.basename(sys.argv[0]) == '__main__.py':
    sys.argv[0] = 'python -m ' + os.path.basename(os.path.dirname(sys.argv[0]))

gather.run(
    commands=main.COMMANDS.collect(),
    version=ncolony.__version__,
    argv=sys.argv[1:],
    output=sys.stdout,
)
