# Copyright (c) Moshe Zadka
# See LICENSE for details.
"""ncolony.directory_monitor
============================

Monitor directories for configuration and messages
"""

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

    def _checkConf():
        currentFiles = set(confFile for confFile in path.globChildren('*')
                           if not confFile.basename().endswith('.new'))
        removed = files - currentFiles
        added = currentFiles - files
        for confFile in added:
            contents = confFile.getContent()
            filesContents[confFile] = contents
            receiver.add(confFile.basename(), contents)
        for confFile in removed:
            receiver.remove(confFile.basename())
        same = currentFiles & files
        for confFile in same:
            newContents = confFile.getContent()
            oldContents = filesContents[confFile]
            if newContents == oldContents:
                continue
            receiver.remove(confFile.basename())
            filesContents[confFile] = newContents
            receiver.add(confFile.basename(), newContents)
        files.clear()
        files.update(currentFiles)
    return _checkConf


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

    def _checkMessages():
        messageFiles = path.globChildren('*')
        for message in messageFiles:
            if message.basename().endswith('.new'):
                continue
            receiver.message(message.getContent())
            message.remove()
    return _checkMessages
