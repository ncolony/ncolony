# Copyright (c) Moshe Zadka
# See LICENSE for details.

"""Functional/integration test for ncolony"""
from __future__ import print_function

import errno
import os
import shutil
import subprocess
import sys
import textwrap
import time

from ncolony import main as mainlib


def _getHere():
    here = __file__
    while not os.path.exists(os.path.join(here, '.gitignore')):
        here = os.path.dirname(here)
    here = os.path.join(here, 'build')
    return here


def _killPatiently(pidFile):
    while os.path.exists(pidFile):
        print('Old process remains -- shutting it down')
        with open(pidFile) as fp:
            pid = int(fp.read())
        try:
            os.kill(pid, 15)
        except OSError as e:
            if e.errno == errno.ESRCH:
                break
            else:
                raise
        time.sleep(5)


@mainlib.COMMANDS.register(name='tests.functional_test')
def main(argv):
    """Run ncolony with a simple process"""
    argv = argv
    envLocation = os.environ['VIRTUAL_ENV']
    binLocation = os.path.join(envLocation, 'bin')

    if sys.executable != os.path.join(binLocation, 'python'):
        sys.exit('Refusing to run on the wrong interpreter '+sys.executable)

    here = _getHere()
    FUNC_TEMP = os.path.join(here, '_func_temp')
    LOG_FILE = os.path.join(FUNC_TEMP, 'twisted.log')
    if os.path.exists(FUNC_TEMP):
        shutil.rmtree(FUNC_TEMP)
    CONFIGS = os.path.join(FUNC_TEMP, 'configs')
    MESSAGES = os.path.join(FUNC_TEMP, 'messages')
    os.makedirs(CONFIGS)
    os.makedirs(MESSAGES)
    locations = ['--messages', MESSAGES,
                 '--config', CONFIGS]
    SLEEP = textwrap.dedent("""
    import time
    import sys

    print('START')
    sys.stdout.flush()
    time.sleep(3)
    print('STOP')
    """)
    SLEEPER = ['--arg=-c', '--arg', SLEEP]
    subprocess.check_call([sys.executable, '-m', 'ncolony', 'ctl'] +
                          locations +
                          ['add', 'sleeper', '--cmd', sys.executable] +
                          SLEEPER)
    proc = subprocess.Popen([sys.executable, '-m', 'twisted',
                             '--log-file', LOG_FILE,
                             'ncolony',
                             '--freq', '1'] +
                            locations)
    for dummy in range(10):
        print('checking for log file')
        try:
            with open(LOG_FILE):
                pass
        except IOError:
            pass
        else:
            break
        time.sleep(1)
    else:
        sys.exit("log file does not exist")
    print("sleeping for 5 seconds")
    time.sleep(5)
    print("waking up, asking for global restart")
    subprocess.check_call([sys.executable, '-m', 'ncolony', 'ctl'] +
                          locations + ['restart-all'])
    print("sleeping for 5 seconds")
    time.sleep(5)
    print("waking up, killing twist")
    proc.terminate()
    for dummy in range(10):
        print('waiting for twist to shutdown')
        if proc.poll() is not None:
            break
        time.sleep(1)
    else:
        sys.exit("twist did not shutdown")
    _analyzeLogFile(LOG_FILE)


def _analyzeLogFile(log_file):
    with open(log_file) as fp:
        lines = list(fp)
    states = [line for line in lines if 'START' in line or 'STOP' in line]
    if 'START' in states[-1]:
        states.pop()
    # Consume in pairs
    states_iter = enumerate(iter(states))
    for i, el in states_iter:
        if 'START' not in el:
            sys.exit('Unexpected STOP %d' % i)
        i, nextEl = next(states_iter)
        if 'START' in nextEl:
            break
    else:
        sys.exit('No restart detected')
    i, nextEl = next(states_iter)
    for i, el in states_iter:
        if 'START' not in el:
            sys.exit('Unexpected STOP %d:%r' % (i, el))
        i, nextEl = next(states_iter)
        if 'START' not in nextEl:
            sys.exit('Unexpected restart')
