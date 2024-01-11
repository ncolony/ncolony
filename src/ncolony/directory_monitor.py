# Copyright (c) Moshe Zadka
# See LICENSE for details.
"""ncolony.directory_monitor
============================

Monitor directories for configuration and messages
"""

import functools
import os

from twisted.python import filepath


def checker(location, receiver):
    """Construct a function that checks a directory for process configuration

    The function checks for additions or removals
    of JSON process configuration files and calls the appropriate receiver
    methods.

    :param location: string, the directory to monitor
    :param receiver: IEventReceiver
    :returns: a function with no parameters
    """
    path = filepath.FilePath(location)
    files = set()
    filesContents = {}

    def _check(path):
        currentFiles = set(fname for fname in os.listdir(location)
                           if not fname.endswith('.new'))
        removed = files - currentFiles
        added = currentFiles - files
        for fname in added:
            contents = path.child(fname).getContent()
            filesContents[fname] = contents
            receiver.add(fname, contents)
        for fname in removed:
            receiver.remove(fname)
        same = currentFiles & files
        for fname in same:
            newContents = path.child(fname).getContent()
            oldContents = filesContents[fname]
            if newContents == oldContents:
                continue
            receiver.remove(fname)
            filesContents[fname] = newContents
            receiver.add(fname, newContents)
        files.clear()
        files.update(currentFiles)
    return functools.partial(_check, path)


def messages(location, receiver):
    """Construct a function that checks a directory for messages

    The function checks for new messages and
    calls the appropriate method on the receiver. Sent messages are
    deleted.

    :param location: string, the directory to monitor
    :param receiver: IEventReceiver
    :returns: a function with no parameters
    """
    path = filepath.FilePath(location)

    def _check(path):
        messageFiles = path.globChildren('*')
        for message in messageFiles:
            if message.basename().endswith('.new'):
                continue
            receiver.message(message.getContent())
            message.remove()
    return functools.partial(_check, path)
