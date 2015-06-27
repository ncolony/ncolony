# Copyright (c) Moshe Zadka
# See LICENSE for details.
"""Main

For use as 'python -m ncolony [reaper|ctl] ...'
"""
import sys

import mainland

if __name__ != '__main__':
    raise ImportError("This module cannot be imported")

mainland.main(
    root='ncolony',
    marker='NCOLONY_MAIN_OK',
    suffix=['lib', ''],
    argv=sys.argv,
)
