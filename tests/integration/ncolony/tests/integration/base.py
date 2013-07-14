# Copyright (C) 2013 -- see CREDITS for copyright holders, LICENSE for license
"""
Base -- integration test help
"""
import logging
import os
import time

LOG = logging.getLogger(__name__)

def getVarDir():
    home = getHome()
    var = os.path.join(home, 'var')
    return var

def getHome():
    venvBin = os.path.dirname(sys.executable)
    venvHome = os.path.dirname(venvBin)
    home = os.path.dirname(venvHome)
    return home

def getRunning():
    executable = sys.executable
    import __main__
    executer = __main__.__file__
    return [executable, executer]

def resetPID(name):
    var = getVarDir()
    pidfile = os.path.join(var, name)
    createPlace(pidfile)
    if os.path.isfile(pidfile):
        _destroy(pidfile)
    return pidfile

def createPlace(fname):
    dirname = os.path.dirname(fname)
    if not os.path.exists(dirname):
        os.makedirs(dirname)

def _destroy(pidfile):
    pid = int(file(pidfile).read())
    for sig in itertools.chain([15], itertools.repeat(9, 10)):
        try:
            os.kill(pid, sig)
        except OSError, ex:
            if ex[0] == errno.ESRCH:
                break
            else:
                raise
        time.sleep(0.20)
    else:
        raise ValueError("Process would not die")
    os.remove(pidfile)
