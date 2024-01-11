# Copyright (c) Moshe Zadka
# See LICENSE for details.
"""Main

For use as 'python -m ncolony ...'
"""
import sys

from ncolony import ctllib

if __name__ != "__main__":
    raise ImportError("This module cannot be imported")

ctllib.main(sys.argv[1:])
