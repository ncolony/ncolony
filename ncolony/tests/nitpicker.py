# Copyright (c) Moshe Zadka
# See LICENSE for details.

"""Automatic nitpicker, so humans won't have to"""

from __future__ import print_function

if __name__ != '__main__':
    raise ImportError("This module is not designed to be imported", __name__)

import difflib
import os
import sys

PROPER_HEADER = """\
# Copyright (c) Moshe Zadka
# See LICENSE for details.
"""

here = sys.argv[0]
while not os.path.exists(os.path.join(here, '.gitignore')):
    here = os.path.dirname(here)

errors = 0
differ = difflib.Differ()

## Check .pyc files
for dirpath, dirnames, filenames in os.walk(here, topdown=True):
    if 'build' in dirpath or '__pycache__' in dirpath:
        dirnames[:] = []
        continue
    for filename in filenames:
        fullname = os.path.join(dirpath, filename)
        if fullname.endswith('.pyc'):
            pyFile = fullname[:-1]
            if not os.path.isfile(pyFile):
                errors += 1
                print("Byte code file with no source:", fullname, file=sys.stderr)
        if fullname.endswith('.py') and not fullname.endswith('versioneer.py'):
            with open(fullname) as fp:
                header = fp.readline()+ fp.readline()
                if header != PROPER_HEADER:
                    errors += 1
                    print("Python file with no header:", fullname, file=sys.stderr)
                    for line in differ.compare(header.splitlines(), PROPER_HEADER.splitlines()):
                        print(line.rstrip(), file=sys.stderr)

if errors:
    sys.exit("NITS PICKED")
