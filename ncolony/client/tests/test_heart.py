# Copyright (c) Moshe Zadka
# See LICENSE for details.
"""ncolony.tests.test_heart -- test heart service"""

from __future__ import division

import json
import os
import unittest

from twisted.python import filepath
from twisted.application import internet as tainternet

from ncolony.client import heart

## pylint: disable=too-few-public-methods

class DummyFile(object):

    """Fake a filepath enough for hearts"""

    def __init__(self):
        self.touched = 0

    def touch(self):
        """Note how many times this method was called"""
        self.touched += 1

## pylint: enable=too-few-public-methods

def replaceEnvironment(case, myEnv=None):
    """Replace environment temporarily, restoring it at end of test

    :params myEnv: a dict-like object
    """
    if myEnv == None:
        myEnv = buildEnv()
    oldEnviron = os.environ
    def _cleanup():
        os.environ = oldEnviron
    case.addCleanup(_cleanup)
    os.environ = myEnv

_MISSING = object()

def _getSelf(method):
    ret = getattr(method, 'im_self', _MISSING)
    if ret is not _MISSING:
        return ret
    ret = getattr(method, '__self__', _MISSING)
    if ret is not _MISSING:
        return ret
    raise TypeError("no self", method)

def _getFunc(method):
    ret = getattr(method, 'im_func', _MISSING)
    if ret is not _MISSING:
        return ret
    ret = getattr(method, '__func__', _MISSING)
    if ret is not _MISSING:
        return ret
    return method

def checkHeartService(case, service, statusName='my.status'):
    """Check that a heart service is correct

    :params case: a unittest.TestCase
    :params service: a heart timer service
    """
    case.assertIsInstance(service, tainternet.TimerService)
    case.assertEquals(service.step, 10/3)
    func, args, kwargs = service.call
    case.assertFalse(args)
    case.assertFalse(kwargs)
    myHeart = _getSelf(func)
    case.assertIs(_getFunc(func), _getFunc(heart.Heart.beat))
    case.assertIsInstance(myHeart, heart.Heart)
    fp = myHeart.getFile()
    case.assertIsInstance(fp, filepath.FilePath)
    case.assertEquals(fp.basename(), statusName)

def buildEnv(params=None):
    """Build an environment with NCOLONY_CONFIG

    :returns: copy of the environment dict and NCOLONY_CONFIG
    """
    if params is None:
        params = dict(status='my.status', period=10, grace=3)
    config = {'ncolony.beatcheck': params}
    configJSON = json.dumps(config)
    myEnv = dict(os.environ)
    myEnv['NCOLONY_CONFIG'] = configJSON
    return myEnv

class TestHeart(unittest.TestCase):

    """Tests for the heart module"""

    def test_heart(self):
        """Test the Heart class"""
        fake = DummyFile()
        myHeart = heart.Heart(path=fake)
        self.assertIs(myHeart.getFile(), fake)
        self.assertEquals(fake.touched, 0)
        myHeart.beat()
        self.assertEquals(fake.touched, 1)
        myHeart.beat()
        self.assertEquals(fake.touched, 2)

    def test_make_service(self):
        """Test make service builds the service based on os.environ"""
        myEnv = buildEnv()
        replaceEnvironment(self, myEnv)
        service = heart.makeService()
        checkHeartService(self, service)

    def test_make_service_default_name(self):
        """Test make service builds the service based on os.environ"""
        params = dict(status='.', period=10, grace=3)
        myEnv = buildEnv(params=params)
        myEnv['NCOLONY_NAME'] = 'hello'
        replaceEnvironment(self, myEnv)
        service = heart.makeService()
        checkHeartService(self, service, 'hello')

    def test_make_service_no_env(self):
        """Test make service builds the service based on os.environ"""
        myEnv = dict(os.environ)
        ## Simplest way to make sure this doesn't exist
        myEnv['NCOLONY_CONFIG'] = None
        del myEnv['NCOLONY_CONFIG']
        replaceEnvironment(self, myEnv)
        self.assertIsNone(heart.makeService())

    def test_make_service_no_beatcheck(self):
        """Test make service builds the service based on os.environ"""
        myEnv = dict(os.environ)
        config = {}
        configJSON = json.dumps(config)
        myEnv = dict(os.environ)
        myEnv['NCOLONY_CONFIG'] = configJSON
        replaceEnvironment(self, myEnv)
        self.assertIsNone(heart.makeService())
