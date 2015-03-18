# Copyright (c) Moshe Zadka
# See LICENSE for details.
"""ncolony.service
==========================================================================

Implement the 'ncolony' twistd plugin.

.. code-block:: bash

  $ twistd ncolony --config <dir> --messages <dir>

Will run a service that brings up all processes described in files
in the configuration directory (and shuts them down if the files
ago away), and listens for restart messages on the messages directory.
"""

from twisted.python import usage
from twisted.application import service as taservice, internet
from twisted.runner import procmon as procmonlib, procmontap

from ncolony import directory_monitor, process_events

## pylint: disable=too-few-public-methods

class TransportDirectoryDict(dict):

    """Dict-like object that writes the 'pid' value to a directory

    This dict-like object assumes all the values have a 'pid' attribute,
    and writes that attribute into a file named the same as the key
    in the given directory.
    """

    def __init__(self, output):
        """Initialize

        :param output: a {twisted.python.filepath.FilePath} object
        """
        super(TransportDirectoryDict, self).__init__()
        self.output = output

    def __setitem__(self, name, value):
        super(TransportDirectoryDict, self).__setitem__(name, value)
        self.output.child(name).setContent(str(value.pid))

    def __delitem__(self, name):
        super(TransportDirectoryDict, self).__delitem__(name)
        self.output.child(name).remove()

## pylint: enable=too-few-public-methods


def get(config, messages, freq, pidDir=None, reactor=None):
    """Return a service which monitors processes based on directory contents

    Construct and return a service that, when started, will run processes
    based on the contents of the 'config' directory, restarting them
    if file contents change and stopping them if the file is removed.

    It also listens for restart and restart-all messages on the 'messages'
    directory.

    :param config: string, location of configuration directory
    :param messages: string, location of messages directory
    :param freq: number, frequency to check for new messages and configuration updates
    :param pidDir: {twisted.python.filepath.FilePath} or None, location to keep pid files
    :param reactor: something implementing the interfaces
                       {twisted.internet.interfaces.IReactorTime} and
                       {twisted.internet.interfaces.IReactorProcess} and
    :returns: service, {twisted.application.interfaces.IService}
    """
    ret = taservice.MultiService()
    args = ()
    if reactor is not None:
        args = reactor,
    procmon = procmonlib.ProcessMonitor(*args)
    if pidDir is not None:
        protocols = TransportDirectoryDict(pidDir)
        procmon.protocols = protocols
    procmon.setName('procmon')
    receiver = process_events.Receiver(procmon)
    confcheck = directory_monitor.checker(config, receiver)
    confserv = internet.TimerService(freq, confcheck)
    confserv.setServiceParent(ret)
    messagecheck = directory_monitor.messages(messages, receiver)
    messageserv = internet.TimerService(freq, messagecheck)
    messageserv.setServiceParent(ret)
    procmon.setServiceParent(ret)
    return ret

## pylint: disable=too-few-public-methods

class Options(usage.Options):

    """Options for ncolony service"""

    optParameters = [
        ["config", None, None, "Directory for configuration"],
        ["messages", None, None, "Directory for messages"],
        ["frequency", None, 10, "Frequency of checking for updates", float],
        ["pid", None, None, "Directory of PID files"],
    ] + procmontap.Options.optParameters

    def postOptions(self):
        """Checks that required messages/config directories are present"""
        for param in ('messages', 'config'):
            if self[param] is None:
                raise usage.UsageError("Missing required", param)

## pylint: enable=too-few-public-methods

def makeService(opt):
    """Return a service based on parsed command-line options

    :param opt: dict-like object. Relevant keys are config, messages,
                pid, frequency, threshold, killtime, minrestartdelay
                and maxrestartdelay
    :returns: service, {twisted.application.interfaces.IService}
    """
    ret = get(config=opt['config'], messages=opt['messages'],
              pidDir=opt['pid'], freq=opt['frequency'])
    pm = ret.getServiceNamed("procmon")
    pm.threshold = opt["threshold"]
    pm.killTime = opt["killtime"]
    pm.minRestartDelay = opt["minrestartdelay"]
    pm.maxRestartDelay = opt["maxrestartdelay"]
    return ret
