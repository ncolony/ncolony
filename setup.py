# Copyright (c) Moshe Zadka
# See LICENSE for details.
import setuptools

import ncolony as module

setuptools.setup(
    url='https://github.com/moshez/ncolony',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: No Input/Output (Daemon)',
        'Framework :: Twisted',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: MIT License',
        'Operating System :: POSIX',
        'Topic :: System',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
    ],
    keywords='process monitoring supervisor daemon',
    packages=[module.__name__, 'twisted.plugins'],
    install_requires=['Twisted'],
    extras_require = {
        'test': ['coverage', 'pylint'],
        'dev': ['wheel'],
    },
    **module.metadata
)
