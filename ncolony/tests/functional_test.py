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

envLocation = os.environ['VIRTUAL_ENV']
binLocation = os.path.join(envLocation, 'bin')

here = sys.argv[0]
while not os.path.exists(os.path.join(here, '.gitignore')):
    here = os.path.dirname(here)
here = os.path.join(here, 'build')

if sys.executable != os.path.join(binLocation, 'python'):
    sys.exit('Refusing to run on the wrong interpreter '+sys.executable)

FUNC_TEMP = os.path.join(here, '_func_temp')
PID_FILE = os.path.join(FUNC_TEMP, 'twistd.pid')
LOG_FILE = os.path.join(FUNC_TEMP, 'twistd.log')
if os.path.exists(FUNC_TEMP):
    while os.path.exists(PID_FILE):
        print 'Old process remains -- shutting it down'
        fp = file(PID_FILE)
        pid = int(fp.read())
        os.kill(pid, 15)
    shutil.rmtree(FUNC_TEMP)
CONFIGS = os.path.join(FUNC_TEMP, 'configs')
MESSAGES = os.path.join(FUNC_TEMP, 'messages')
os.makedirs(CONFIGS)
os.makedirs(MESSAGES)
DEFAULTS = ['--messages', MESSAGES, '--config', CONFIGS]
SLEEP = "import time, sys;print 'START';sys.stdout.flush();time.sleep(3);print 'STOP'"
SLEEPER = ['--arg=-c', '--arg', SLEEP]
subprocess.check_call([sys.executable, '-m', 'ncolony.ctl'] + DEFAULTS +
                      ['add', 'sleeper', '--cmd', sys.executable] + SLEEPER)
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
STATES = [line for line in LINES if 'START' in line or 'STOP' in line]
if 'START' in STATES[-1]:
    STATES.pop()
## Consume in pairs
STATES_ITER = enumerate(iter(STATES))
for i, el in STATES_ITER:
    if 'START' not in el:
        sys.exit('Unexpected STOP %d' % i)
    i, nextEl = next(STATES_ITER)
    if 'START' in nextEl:
        break
else:
    sys.exit('No restart detected')
i, nextEl = next(STATES_ITER)
for i, el in STATES_ITER:
    if 'START' not in el:
        sys.exit('Unexpected STOP %d:%r' % (i, el))
    i, nextEl = next(STATES_ITER)
    if 'START' not in nextEl:
        sys.exit('Unexpected restart')
