# Copyright (c) Moshe Zadka
# See LICENSE for details.
"""ncolony.schedulelib
========================

Construct a Twisted service for process scheduling.

.. code-block:: bash

   $ twistd -n ncolonysched --timeout 2 --grace 1 --frequency 10 --arg /bin/echo --arg hello
"""
from __future__ import print_function

import os

from zope import interface

from twisted.python import usage

from twisted.internet import interfaces as tiinterfaces
from twisted.internet import defer
from twisted.internet import error as tierror
from twisted.internet import reactor as tireactor

from twisted.application import internet as tainternet, service

from ncolony.client import heart

@interface.implementer(tiinterfaces.IProcessProtocol)
class ProcessProtocol(object):

    """Process protocol that manages short-lived processes"""

    def __init__(self, deferred):
        self.deferred = deferred

    ## pylint: disable=no-self-use
    def childDataReceived(self, fd, data):
        """Log data from process

        :params fd: File descriptor data is coming from
        :params data: The bytes the process returned
        """
        for line in data.splitlines():
            print('[%d]' % fd, line)
    ## pylint: enable=no-self-use

    def processEnded(self, reason):
        """Report process end to deferred

        :params reason: a Failure
        """
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
    """Run a process, return a deferred that fires when it is done

    :params args: Process arguments
    :params timeout: Time before terminating process
    :params grace: Time before killing process after terminating it
    :params reactor: IReactorProcess and IReactorTime
    :returns: deferred that fires with success when the process ends,
              or fails if there was a problem spawning/terminating
              the process
    """
    deferred = defer.Deferred()
    protocol = ProcessProtocol(deferred)
    process = reactor.spawnProcess(protocol, args[0], args, env=os.environ)
    def _logEnded(err):
        err.trap(tierror.ProcessDone, tierror.ProcessTerminated)
        print(err.value)
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
    """Make scheduler service

    :params opts: dict-like object.
       keys: frequency, args, timeout, grace
    """
    ser = tainternet.TimerService(opts['frequency'], runProcess, opts['args'],
                                  opts['timeout'], opts['grace'], tireactor)
    ret = service.MultiService()
    ser.setName('scheduler')
    ser.setServiceParent(ret)
    heart.maybeAddHeart(ret)
    return ret
