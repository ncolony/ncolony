# Copyright (c) Moshe Zadka
# See LICENSE for details.
"""Run one process, reap it and adopted children"""

import argparse
import collections
import functools
import os
import signal
import subprocess
import time
import traceback

SyncReactor = collections.namedtuple('SyncReactor', 'install run wait sleep')

NCOLONY_MAIN_OK = True

def reap(reactor, specialPid):
    """Reap children, stop when reaping expected child

    Reap children. When the correct child is reaped,
    exit.
    """
    while True:
        pid, dummy_status = reactor.wait()
        if pid == specialPid:
            return

def _install(reactor, target):
    for signum in [signal.SIGTERM, signal.SIGINT, signal.SIGALRM]:
        reactor.install(signum, target)

def installSignals(reactor):
    """Install signal handlers

    Install signal handlers that throw exception and ignore
    further signals.
    """
    def _ignoreSignalsAndRaise(signum, dummy_frame):
        _install(reactor, signal.SIG_IGN)
        raise SystemError('Signal sent', signum)
    _install(reactor, _ignoreSignalsAndRaise)

PARSER = argparse.ArgumentParser()
PARSER.add_argument('command', nargs='+', help='Actual command to run')

## pylint: disable=bare-except
def baseMain(reactor, argv):
    """Main loop

    Install signals, run command and wait for child to die.
    If an unexpected exception is raised, print traceback.
    Before exiting, terminate child and then kill it.
    """
    installSignals(reactor)
    args = PARSER.parse_args(argv[1:])
    process = reactor.run(args.command)
    try:
        reap(reactor, process.pid)
    except (KeyboardInterrupt, SystemError):
        pass
    except:
        traceback.print_exc()
    finally:
        process.terminate()
        for dummy in range(30):
            ret = process.poll()
            if ret is not None:
                break
            reactor.sleep(1)
        else:
            process.kill()
## pylint: enable=bare-except

main = functools.partial(baseMain,
                         SyncReactor(install=signal.signal,
                                     run=subprocess.Popen,
                                     wait=os.wait,
                                     sleep=time.sleep))
