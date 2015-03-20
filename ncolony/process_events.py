# Copyright (c) Moshe Zadka
# See LICENSE for details.
"""ncolony.process_events
=========================

Convert events into process monitoring actions.
"""

import json

from zope import interface

from twisted.python import log

from ncolony import interfaces

VALID_KEYS = frozenset(['args', 'uid', 'gid', 'env'])

class Receiver(object):

    """A wrapper around ProcessMonitor that responds to events

    :params monitor: a ProcessMonitor
    """

    interface.implements(interfaces.IMonitorEventReceiver)

    def __init__(self, monitor):
        """Initialize from ProcessMonitor"""
        self.monitor = monitor

    def add(self, name, contents):
        """Add a process

        :params name: string, name of process
        :params contents: string, contents
           parsed as JSON for process params
        :returns: None
        """
        parsedContents = json.loads(contents)
        parsedContents = {key: value
                          for key, value in parsedContents.iteritems()
                          if key in VALID_KEYS}
        parsedContents['name'] = name
        parsedContents['env'] = parsedContents.get('env', {})
        parsedContents['env']['NCOLONY_CONFIG'] = contents
        parsedContents['env']['NCOLONY_NAME'] = name
        self.monitor.addProcess(**parsedContents)
        log.msg("Added monitored process: ", name)

    def remove(self, name):
        """Remove a process

        :params name: string, name of process
        """
        self.monitor.removeProcess(name)
        log.msg("Removed monitored process: ", name)

    def message(self, contents):
        """Respond to a restart or a restart-all message

        :params contents: string, contents of message
           parsed as JSON, and assumed to have a 'type'
           key, with value either 'restart' or 'restart-all'.
           If the value is 'restart', another key
           ('value') should exist with a logical process
           name.
        """
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
