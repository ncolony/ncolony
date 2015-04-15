# Copyright (c) Moshe Zadka
# See LICENSE for details.
"""Reaper

Run a process, reap accidental children, and terminate
the process when we go down.
"""
from ncolony import reaperlib

if __name__ != '__main__':
    raise ImportError("This module cannot be imported")

reaperlib.main()
