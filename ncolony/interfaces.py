# Copyright (c) Moshe Zadka
# See LICENSE for details.

"""ncolony.interfaces -- interface definitions"""

from zope import interface

## pylint: disable=no-self-argument,no-init

class IMonitorEventReceiver(interface.Interface):

    """Event sink when directory changes are noticed"""

    def add(name, contents):
        """New file appeared"""
        pass

    def remove(name):
        """File went away"""
        pass

    def message(contents):
        """New message"""
        pass
