# Copyright (c) Moshe Zadka
# See LICENSE for details.

"""ncolony -- a process starter/monitor"""

from ncolony._version import __version__ as _abstract_version

__version__ = str(_abstract_version)

_long_description = '''\
ncolony_: A wrapper around Twisted process monitor which allows runtime configuration via file-based communication

.. _ncolony: https://ncolony.rtfd.org
'''

metadata = dict(
    name='ncolony',
    description='A process starter/monitor',
    long_description=_long_description,
    author='Moshe Zadka',
    author_email='zadka.moshe@gmail.com',
    license='MIT',
    copyright='2015',
)
