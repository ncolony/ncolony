# Copyright (c) Moshe Zadka
# See LICENSE for details.
"""ncolony.process_events -- convert events into process monitoring actions"""
import json

from zope import interface

from twisted.python import log

from ncolony import interfaces

VALID_KEYS = frozenset(['args', 'uid', 'gid', 'env'])

class Receiver(object):

    """A wrapper around ProcessMonitor that responds to events"""

    interface.implements(interfaces.IMonitorEventReceiver)

    def __init__(self, monitor):
        """Initialize from ProcessMonitor"""
        self.monitor = monitor

    def add(self, name, contents):
        """Add a process"""
        contents = json.loads(contents)
        contents = {key: value
                    for key, value in contents.iteritems()
                    if key in VALID_KEYS}
        contents['name'] = name
        self.monitor.addProcess(**contents)
        log.msg("Added monitored process: ", name)

    def remove(self, name):
        """Remove a process"""
        self.monitor.removeProcess(name)
        log.msg("Removed monitored process: ", name)

    def message(self, contents):
        """Respond to a restart or a restart-all message"""
        contents = json.loads(contents)
        tp = contents['type']
        if tp == 'RESTART':
            self.monitor.stopProcess(contents['name'])
            log.msg("Restarting monitored process: ", contents['name'])
        elif tp == 'RESTART-ALL':
            self.monitor.restartAll()
            log.msg("Restarting all monitored processes")
        else:
            raise ValueError('unknown type', contents)
