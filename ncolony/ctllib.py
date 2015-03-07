# Copyright (c) Moshe Zadka
# See LICENSE for details.

"""ncolony.ctl -- send control messages to the ncolony service"""

import argparse
import collections
import functools
import itertools
import json
import os

from twisted.python import filepath

NEXT = functools.partial(next, itertools.count(0))

Places = collections.namedtuple('Places', 'config messages')

## pylint: disable=too-many-arguments
def add(places, name, cmd, args, env=None, uid=None, gid=None):
    """Add a process"""
    args = [cmd]+args
    config = filepath.FilePath(places.config)
    fle = config.child(name)
    details = dict(args=args)
    if env is not None:
        newEnv = {}
        for thing in env:
            name, value = thing.split('=', 1)
            newEnv[name] = value
        details['env'] = newEnv
    if uid is not None:
        details['uid'] = uid
    if gid is not None:
        details['gid'] = gid
    content = json.dumps(details)
    fle.setContent(content)
## pylint: enable=too-many-arguments

def remove(places, name):
    """Remove a process"""
    config = filepath.FilePath(places.config)
    fle = config.child(name)
    fle.remove()

def _addMessage(places, content):
    messages = filepath.FilePath(places.messages)
    name = '%03dMessage.%s' % (NEXT(), os.getpid())
    message = messages.child(name)
    message.setContent(content)

def restart(places, name):
    """Restart a process"""
    content = json.dumps(dict(type='RESTART', name=name))
    _addMessage(places, content)

def restartAll(places):
    """Restart all processes"""
    content = json.dumps(dict(type='RESTART-ALL'))
    _addMessage(places, content)

PARSER = argparse.ArgumentParser()
PARSER.add_argument('--messages', required=True)
PARSER.add_argument('--config', required=True)
_subparsers = PARSER.add_subparsers()
_restart_all_parser = _subparsers.add_parser('restart-all')
_restart_all_parser.set_defaults(func=restartAll)
_restart_parser = _subparsers.add_parser('restart')
_restart_parser.add_argument('name')
_restart_parser.set_defaults(func=restart)
_remove_parser = _subparsers.add_parser('remove')
_remove_parser.add_argument('name')
_remove_parser.set_defaults(func=remove)
_add_parser = _subparsers.add_parser('add')
_add_parser.add_argument('name')
_add_parser.add_argument('--cmd', required=True)
_add_parser.add_argument('--arg', dest='args', action='append')
_add_parser.add_argument('--env', action='append')
_add_parser.add_argument('--uid', type=int)
_add_parser.add_argument('--gid', type=int)
_add_parser.set_defaults(func=add)

def call(results):
    """Call results.func on the attributes of results"""
    results = vars(results)
    places = Places(config=results.pop('config'), messages=results.pop('messages'))
    func = results.pop('func')
    func(places, **results)

def main():
    """command-line entry point"""
    ns = PARSER.parse_args()
    call(ns)
