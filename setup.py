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

class CoverageTrialCommand(OptionLessCommand):

    def run(self):
        trial = spawn.find_executable('trial')
        tempDir = os.path.join(os.path.dirname(sys.argv[0]), 'build', '_trial_temp')
        command = ['coverage', 'run', trial, '--temp-directory', tempDir, module.__name__]
        subprocess.check_call(command)
        testDir = os.path.join(module.__name__, 'tests', '*')
        interfaceModules = os.path.join(module.__name__, 'interfaces*')
        omit = ','.join([testDir, interfaceModules])
        include = module.__name__+'*'
        command = ['coverage', 'report', '--include', include, '--omit', omit,
                   '--show-missing', '--fail-under=100']
        subprocess.check_call(command)

class FunctionalTests(OptionLessCommand):

    def run(self):
        command = [sys.executable, '-m', module.__name__+'.tests.functional_test']
        subprocess.check_call(command)

class Lint(OptionLessCommand):

    def run(self):
        command = ['pylint', '--rcfile', 'admin/pylintrc', module.__name__]
        subprocess.check_call(command)

class All(OptionLessCommand):

    def run(self):
        self.run_command('test')
        self.run_command('lint')
        self.run_command('integration')
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
        'test': ['coverage', 'pylint'],
        'dev': ['wheel'],
    },
    cmdclass=dict(test=CoverageTrialCommand, integration=FunctionalTests, lint=Lint, all=All),
    **module.metadata
)
