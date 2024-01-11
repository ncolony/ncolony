# Copyright (c) Moshe Zadka
# See LICENSE for details.
"""ncolony.process_events
=========================

Convert events into process monitoring actions.
"""

import collections
import json
import os

import six

from zope import interface

from twisted.python import log

from ncolony import interfaces

VALID_KEYS = frozenset(['args', 'uid', 'gid', 'env', 'env_inherit', 'group'])


@interface.implementer(interfaces.IMonitorEventReceiver)
class Receiver(object):

    """A wrapper around ProcessMonitor that responds to events

    :params monitor: a ProcessMonitor
    """

    def __init__(self, monitor, environ=None):
        """Initialize from ProcessMonitor"""
        if environ is None:
            environ = os.environ
        self.environ = environ
        self.monitor = monitor
        self._groupToProcess = collections.defaultdict(set)
        self._processToGroups = {}

    def add(self, name, contents):
        """Add a process

        :params name: string, name of process
        :params contents: string, contents
           parsed as JSON for process params
        :returns: None
        """
        parsedContents = json.loads(contents.decode('utf-8'))
        parsedContents = {key: value
                          for key, value in six.iteritems(parsedContents)
                          if key in VALID_KEYS}
        parsedContents['name'] = name
        parsedContents['env'] = parsedContents.get('env', {})
        for key in parsedContents.pop('env_inherit', []):
            parsedContents['env'][key] = self.environ.get(key, '')
        groups = parsedContents.pop('group', [])
        for key in groups:
            self._groupToProcess[key].add(name)
        self._processToGroups[name] = groups
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
        for group in self._processToGroups.pop(name):
            self._groupToProcess[group].remove(name)

    def message(self, contents):
        """Respond to a restart or a restart-all message

        :params contents: string, contents of message
           parsed as JSON, and assumed to have a 'type'
           key, with value either 'restart' or 'restart-all'.
           If the value is 'restart', another key
           ('value') should exist with a logical process
           name.
        """
        contents = json.loads(contents.decode('utf-8'))
        tp = contents['type']
        if tp == 'RESTART':
            self.monitor.stopProcess(contents['name'])
            log.msg("Restarting monitored process: ", contents['name'])
        elif tp == 'RESTART-ALL':
            self.monitor.restartAll()
            log.msg("Restarting all monitored processes")
        elif tp == 'RESTART-GROUP':
            log.msg("Restarting group", contents['group'])
            for name in self._groupToProcess[contents['group']]:
                log.msg("Restarting monitored process: ", name)
                self.monitor.stopProcess(name)
        else:
            raise ValueError('unknown type', contents)
