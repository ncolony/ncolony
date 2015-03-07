# Copyright (c) Moshe Zadka
# See LICENSE for details.

"""ncolony.ctl -- intended to be used via python -m"""

if __name__ != '__main__':
    raise ImportError("This module is not designed to be imported")

from ncolony import ctllib

ctllib.main()
