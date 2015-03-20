# Copyright (c) Moshe Zadka
# See LICENSE for details.
from distutils import cmd, spawn

import os
import subprocess
import sys

import setuptools

import ncolony as module

class OptionLessCommand(cmd.Command):

    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

class ToxTestCommand(OptionLessCommand):

    def run(self):
        subprocess.check_call(['tox'])

class All(OptionLessCommand):

    def run(self):
        self.run_command('test')
        self.run_command('bdist_wheel')
        self.run_command('build_sphinx')

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
        'test': ['tox'],
        'dev': ['wheel', 'sphinx'],
    },
    cmdclass=dict(test=ToxTestCommand, all=All),
    **module.metadata
)
