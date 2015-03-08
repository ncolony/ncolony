# Copyright (c) Moshe Zadka
# See LICENSE for details.

"""ncolony.interfaces
======================

Interface definitions

.. py:class:: IMonitorEventReceiver

   .. py:method:: add

      New file appeared

      :params name: string, file name
      :params contents: string, file contents
      :returns: None

   .. py:method:: remove

      File went away

      :params name: string, file name
      :returns: None

   .. py:method:: message

      Message sent

      :params contents: string, message contents
      :returns: None
"""

from zope import interface

__all__ = ['IMonitorEventReceiver']

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
