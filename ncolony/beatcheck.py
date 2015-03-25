# Copyright (c) Moshe Zadka
# See LICENSE for details.

"""ncolony.beatcheck
====================

Check heartbeats of processes that should beat.

Usually used as

$ twistd -n ncolony_beatcheck --config config --messages messages

It will watch the configurations, and send a restart message
for any process that does not beat within its heartbeat.
Processes are encouraged to try and beat about 3-4 times
faster than the minimum, so that they can miss one beat, and
account for slight timer inaccuracies, and still not be considered
unhealthy.
"""

import functools
import json
import time

from twisted.python import filepath, usage

from twisted.application import internet as tainternet

from ncolony import ctllib
from ncolony.client import heart

def check(path, start, now):
    """check which processes need to be restarted

    :params path: a twisted.python.filepath.FilePath with configurations
    :params start: when the checker started running
    :params now: current time
    :returns: list of strings
    """
    return [child.basename() for child in path.children()
            if _isbad(child, start, now)]

def _isbad(child, start, now):
    content = child.getContent()
    parsed = json.loads(content)
    params = parsed.get('ncolony.beatcheck')
    if params is None:
        return False
    period = params['period']
    grace = params['grace']
    mtime = max(child.getModificationTime(), start)
    if mtime + period*grace >= now:
        return False
    status = params['status']
    statusPath = child.clonePath(status)
    if not statusPath.exists():
        return True
    if statusPath.isdir():
        statusPath = statusPath.child(child.basename())
    statusMtime = statusPath.getModificationTime()
    return (statusMtime + period) < now

def run(restarter, checker, timer):
    """Run restarter on the checker's output

    :params restarter: something to run on the output of the checker
    :params checker: a function expected to get one argument (current time)
                     and return a list of stale names
    :params timer: a function of zero arguments, intended to return current time
    :returns: None
    """
    for bad in checker(timer()):
        restarter(bad)

def parseConfig(opt):
    """Parse configuration

    :params opt: dict-like object with config and messages keys
    :returns: restarter, path
    """
    places = ctllib.Places(config=opt['config'], messages=opt['messages'])
    restarter = functools.partial(ctllib.restart, places)
    path = filepath.FilePath(opt['config'])
    return restarter, path

def makeService(opt):
    """Make a service

    :params opt: dictionary-like object with 'freq', 'config' and 'messages'
    :returns: twisted.application.internet.TimerService that at opt['freq']
              checks for stale processes in opt['config'], and sends
              restart messages through opt['messages']
    """
    restarter, path = parseConfig(opt)
    now = time.time()
    checker = functools.partial(check, path, now)
    beatcheck = tainternet.TimerService(opt['freq'], run, restarter, checker, time.time)
    beatcheck.setName('beatcheck')
    return heart.wrapHeart(beatcheck)

## pylint: disable=too-few-public-methods

class Options(usage.Options):

    """Options for ncolony beatcheck service"""

    optParameters = [
        ["messages", None, None, "Directory for messages"],
        ["config", None, None, "Directory for configuration"],
        ["freq", None, 10, "Frequency of checking for updates", float],
    ]

    def postOptions(self):
        """Checks that required messages/config directories are present"""
        for param in ('messages', 'config'):
            if self[param] is None:
                raise usage.UsageError("Missing required", param)

## pylint: enable=too-few-public-methods
