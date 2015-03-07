# Copyright (c) Moshe Zadka
# See LICENSE for details.

"""Functional/integration test for ncolony"""

if __name__ != '__main__':
    raise ImportError("This module is not designed to be imported", __name__)

import os
import shutil
import subprocess
import sys
import time

try:
    envLocation = os.environ['VIRTUAL_ENV']
except KeyError:
    sys.exit('Refusing to run without a virtual environment')

binLocation = os.path.join(envLocation, 'bin')
here = sys.argv[0]
while not os.path.exists(os.path.join(here, '.gitignore')):
    here = os.path.dirname(here)
here = os.path.join(here, 'build')

if sys.executable != os.path.join(binLocation, 'python'):
    sys.exit('Refusing to run on the wrong interpreter '+sys.executable)

FUNC_TEMP = os.path.join(here, '_func_temp')
if os.path.exists(FUNC_TEMP):
    shutil.rmtree(FUNC_TEMP)
CONFIGS = os.path.join(FUNC_TEMP, 'configs')
MESSAGES = os.path.join(FUNC_TEMP, 'messages')
os.makedirs(CONFIGS)
os.makedirs(MESSAGES)
DEFAULTS = ['--messages', MESSAGES, '--config', CONFIGS]
SLEEP = "import time, sys;print 'START';sys.stdout.flush();time.sleep(2);print 'STOP'"
SLEEPER = ['--arg=-c', '--arg', SLEEP]
subprocess.check_call([sys.executable, '-m', 'ncolony.ctl'] + DEFAULTS +
                      ['add', 'sleeper', '--cmd', sys.executable] + SLEEPER)
PID_FILE = os.path.join(FUNC_TEMP, 'twistd.pid')
LOG_FILE = os.path.join(FUNC_TEMP, 'twistd.log')
subprocess.check_call([os.path.join(binLocation, 'twistd'), '--logfile', LOG_FILE,
                       '--pidfile', PID_FILE, 'ncolony'] +
                      DEFAULTS +
                      ['--freq', '1'])
for i in range(10):
    print 'checking for pid file'
    try:
        fp = file(PID_FILE)
    except IOError:
        continue
    else:
        break
    time.sleep(1)
else:
    sys.exit("PID file does not exist")
pid = int(fp.read())
print "sleeping for 5 seconds"
time.sleep(5)
print "waking up, asking for global restart"
subprocess.check_call([sys.executable, '-m', 'ncolony.ctl'] + DEFAULTS + ['restart-all'])
print "sleeping for 5 seconds"
time.sleep(5)
print "waking up, killing twistd"
os.kill(pid, 15)
for i in range(10):
    print 'waiting for twistd to shutdown'
    if not os.path.exists(PID_FILE):
        break
    time.sleep(1)
else:
    sys.exit("twistd did not shutdown")
LINES = list(file(LOG_FILE))
STARTS = sum(1 for line in LINES if 'START' in line)
STOPS = sum(1 for line in LINES if 'STOP' in line)
if STARTS != 6:
    sys.exit('Wrong number of START messages: %d' % STARTS)
if STOPS != 4:
    sys.exit('Wrong number of STOP messages: %d' % STOPS)
