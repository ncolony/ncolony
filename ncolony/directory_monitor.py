# Copyright (c) Moshe Zadka
# See LICENSE for details.
"""ncolony.directory_monitor -- monitor directories for configuration and messages"""

import os

from twisted.python import filepath

def checker(location, receiver):
    """Construct a function that checks a directory for process configuration

    Construct a function that, when called, checks for additions or removals
    of JSON process configuration files and calls the appropriate receiver
    methods.
    """
    path = filepath.FilePath(location)
    files = set()
    filesContents = {}
    def _check():
        currentFiles = set(fname for fname in os.listdir(location) if not fname.endswith('.new'))
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
    return _check

def messages(location, receiver):
    """Construct a function that checks a directory for messages

    Construct a function that, when called, checks for new messages and
    calls the appropriate method on the receiver. Sent messages are
    deleted.
    """
    path = filepath.FilePath(location)
    def _check():
        messageFiles = path.globChildren('*')
        for message in messageFiles:
            if message.basename().endswith('.new'):
                continue
            receiver.message(message.getContent())
            message.remove()
    return _check
