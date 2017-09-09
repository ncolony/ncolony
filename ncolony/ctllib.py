# Copyright (c) Moshe Zadka
# See LICENSE for details.

"""ncolony.ctllib
===================================================================

This module can be used either as a library from Python or as a
commandline using the wrapper :code:`ctl` via

.. code-block:: bash

   $ python -m ncolony ctl <arguments>

Description of the service's interface is in <figure out how
to do a back-reference>.

The add/remove messages add/remove configuration files for processes.
Since removal of a configuration is equivalent to killing the process,
nothing else nees to be done to rid of needed processes.

All functions which are meant to be used as a library API

Add is the most complicated function, because it needs to be able
to express every aspect of the process. It allows control of the
name, command, arguments, environment variables and uid/gid.

Removal is pretty simple, since it only needs the name.

Restart also needs just the name.

Restart-all does not need even the name, since it restarts
all processes.
"""

import argparse
import collections
import functools
import itertools
import json
import os

from twisted.python import filepath

from ncolony import main as mainlib

NEXT = functools.partial(next, itertools.count(0))

Places = collections.namedtuple('Places', 'config messages')

def _dumps(stuff):
    return json.dumps(stuff).encode('utf-8')

## pylint: disable=too-many-arguments
def add(places, name, cmd, args, env=None, uid=None, gid=None, extras=None):
    """Add a process.

    :param places: a Places instance
    :param name: string, the logical name of the process
    :param cmd: string, executable
    :param args: list of strings, command-line arguments
    :param env: dictionary mapping strings to strings
         (will be environment in subprocess)
    :param uid: integer, uid to run the new process as
    :param gid: integer, gid to run the new process as
    :returns: None
    """
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
    if extras is not None:
        details.update(extras)
    content = _dumps(details)
    fle.setContent(content)
## pylint: enable=too-many-arguments

def remove(places, name):
    """Remove a process

    :params places: a Places instance
    :params name: string, the logical name of the process
    :returns: None
    """
    config = filepath.FilePath(places.config)
    fle = config.child(name)
    fle.remove()

def _addMessage(places, content):
    messages = filepath.FilePath(places.messages)
    name = '%03dMessage.%s' % (NEXT(), os.getpid())
    message = messages.child(name)
    message.setContent(content)

def restart(places, name):
    """Restart a process

    :params places: a Places instance
    :params name: string, the logical name of the process
    :returns: None
    """
    content = _dumps(dict(type='RESTART', name=name))
    _addMessage(places, content)

def restartAll(places):
    """Restart all processes

    :params places: a Places instance
    :returns: None
    """
    content = _dumps(dict(type='RESTART-ALL'))
    _addMessage(places, content)

def _parseJSON(fname):
    with open(fname) as fp:
        data = fp.read()
    return json.loads(data)

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
_add_parser.add_argument('--extras', type=_parseJSON)
_add_parser.set_defaults(func=add)

def call(results):
    """Call results.func on the attributes of results

    :params result: dictionary-like object
    :returns: None
    """
    results = vars(results)
    places = Places(config=results.pop('config'), messages=results.pop('messages'))
    func = results.pop('func')
    func(places, **results)

@mainlib.COMMANDS.register(name='ctl')
def main(argv):
    """command-line entry point

        --messages: messages directory

        --config: configuration directory

    subcommands:
        add:
            name (positional)

            --cmd (required) -- executable

            --arg -- add an argument

            --env -- add an environment variable (VAR=value)

            --uid -- set uid

            --gid -- set gid

        remove:
            name (positional)
        restart:
            name (positional)
        restart-all:
            no arguments
    """
    ns = PARSER.parse_args(argv[1:])
    call(ns)
