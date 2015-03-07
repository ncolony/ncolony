# Copyright (c) Moshe Zadka
# See LICENSE for details.
"""ncolony.schedulelib -- construct a Twisted service for process scheduling"""

import os

from zope import interface

from twisted.python import usage

from twisted.internet import interfaces as tiinterfaces
from twisted.internet import defer
from twisted.internet import error as tierror
from twisted.internet import reactor as tireactor

from twisted.application import internet as tainternet

class ProcessProtocol(object):

    """Process protocol that manages short-lived processes"""

    interface.implements(tiinterfaces.IProcessProtocol)

    def __init__(self, deferred):
        self.deferred = deferred

    ## pylint: disable=no-self-use
    def childDataReceived(self, fd, data):
        """Log data from process"""
        for line in data.splitlines():
            print '[%d]' % fd, line
    ## pylint: enable=no-self-use

    def processEnded(self, reason):
        """Report process end to deferred"""
        self.deferred.errback(reason)

    def processExited(self, reason):
        """Ignore processExited"""
        pass

    def childConnectionLost(self, reason):
        """Ignore childConnectionLoss"""
        pass

    def makeConnection(self, transport):
        """Ignore makeConnection"""
        pass

def runProcess(args, timeout, grace, reactor):
    """Run a process, return a deferred that fires when it is done"""
    deferred = defer.Deferred()
    protocol = ProcessProtocol(deferred)
    process = reactor.spawnProcess(protocol, args[0], args, env=os.environ)
    def _logEnded(err):
        err.trap(tierror.ProcessDone, tierror.ProcessTerminated)
        print err.value
    deferred.addErrback(_logEnded)
    def _cancelTermination(dummy):
        for termination in terminations:
            if termination.active():
                termination.cancel()
    deferred.addCallback(_cancelTermination)
    terminations = []
    terminations.append(reactor.callLater(timeout, process.signalProcess, "TERM"))
    terminations.append(reactor.callLater(timeout+grace, process.signalProcess, "KILL"))
    return deferred

class Options(usage.Options):

    """Options for scheduler service"""

    optParameters = [
        ['timeout', None, None, 'Time before terminating the command', int],
        ['grace', None, None,
         'Time between terminating the command and sending an umaskable kill', int],
        ['frequency', None, None, 'How often to run the command', int],
    ]

    def __init__(self):
        usage.Options.__init__(self)
        self['args'] = []

    def opt_arg(self, arg):
        """Argument"""
        self['args'].append(arg)

    def postOptions(self):
        for elem in ['args', 'timeout', 'grace', 'frequency']:
            if not self[elem]:
                raise ValueError(elem)

def makeService(opts):
    """Make scheduler service"""
    ret = tainternet.TimerService(opts['frequency'], runProcess, opts['args'],
                                  opts['timeout'], opts['grace'], tireactor)
    return ret
