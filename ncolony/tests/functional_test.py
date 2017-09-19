# Copyright (c) Moshe Zadka
# See LICENSE for details.

"""Functional/integration test for ncolony"""
from __future__ import print_function

import errno
import os
import shutil
import subprocess
import sys
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
    PID_FILE = os.path.join(FUNC_TEMP, 'twistd.pid')
    LOG_FILE = os.path.join(FUNC_TEMP, 'twistd.log')
    if os.path.exists(FUNC_TEMP):
        _killPatiently(PID_FILE)
        shutil.rmtree(FUNC_TEMP)
    CONFIGS = os.path.join(FUNC_TEMP, 'configs')
    MESSAGES = os.path.join(FUNC_TEMP, 'messages')
    os.makedirs(CONFIGS)
    os.makedirs(MESSAGES)
    DEFAULTS = ['--messages', MESSAGES, '--config', CONFIGS]
    SLEEP = "import time, sys;print('START');sys.stdout.flush();time.sleep(3);print('STOP')"
    SLEEPER = ['--arg=-c', '--arg', SLEEP]
    subprocess.check_call([sys.executable, '-m', 'ncolony', 'ctl'] + DEFAULTS +
                          ['add', 'sleeper', '--cmd', sys.executable] + SLEEPER)
    subprocess.check_call([os.path.join(binLocation, 'twistd'), '--logfile', LOG_FILE,
                           '--pidfile', PID_FILE, 'ncolony'] +
                          DEFAULTS +
                          ['--freq', '1'])
    for dummy in range(10):
        print('checking for pid file')
        try:
            with open(PID_FILE) as fp:
                pid = int(fp.read())
        except IOError:
            continue
        else:
            break
        time.sleep(1)
    else:
        sys.exit("PID file does not exist")
    print("sleeping for 5 seconds")
    time.sleep(5)
    print("waking up, asking for global restart")
    subprocess.check_call([sys.executable, '-m', 'ncolony', 'ctl'] + DEFAULTS + ['restart-all'])
    print("sleeping for 5 seconds")
    time.sleep(5)
    print("waking up, killing twistd")
    os.kill(pid, 15)
    for dummy in range(10):
        print('waiting for twistd to shutdown')
        if not os.path.exists(PID_FILE):
            break
        time.sleep(1)
    else:
        sys.exit("twistd did not shutdown")
    _analyzeLogFile(LOG_FILE)

def _analyzeLogFile(log_file):
    with open(log_file) as fp:
        lines = list(fp)
    states = [line for line in lines if 'START' in line or 'STOP' in line]
    if 'START' in states[-1]:
        states.pop()
    ## Consume in pairs
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
