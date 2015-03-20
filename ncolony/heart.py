# Copyright (c) Moshe Zadka
# See LICENSE for details.

"""ncolony.heart
==================

A heart beater.
"""
from __future__ import division

import json
import os

from twisted.python import filepath
from twisted.application import internet as tainternet

class Heart(object):

    """A Heart.

    Each beat touches a file.
    """
    def __init__(self, path):
        self.path = path

    def getFile(self):
        """Get the file being touched"""
        return self.path

    def beat(self):
        """Touch the file"""
        self.path.touch()

def makeService():
    """Make a service

    :returns: an IService
    """
    configJSON = os.environ.get('NCOLONY_CONFIG')
    if configJSON is None:
        return
    config = json.loads(configJSON)
    params = config.get('ncolony.beatcheck')
    if params is None:
        return
    heart = Heart(filepath.FilePath(params['status']))
    ret = tainternet.TimerService(params['period']/3, heart.beat)
    return ret

def maybeAddHeart(master):
    """Add a heart to a service collection

    Add a heart to a service.IServiceCollector if
    the heart is not None.

    :params master: a service.IServiceCollector
    """
    heartSer = makeService()
    if heartSer is None:
        return
    heartSer.setName('heart')
    heartSer.setServiceParent(master)
