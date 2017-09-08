# Copyright (c) Moshe Zadka
# See LICENSE for details.

"""Tests for ncolony.beatcheck"""

import functools
import os
import shutil
import time
import unittest

from twisted.python import filepath, usage

from twisted.application import internet as tainternet

from ncolony import beatcheck, ctllib
from ncolony.client.tests import test_heart
from ncolony.tests import helper

class TestBeatChecker(unittest.TestCase):

    """Test the beat checker"""

    def setUp(self):
        self.path = os.path.abspath('dummy-config')
        self.messages = os.path.abspath('dummy-messages')
        self.status = os.path.abspath('dummy-status')
        paths = (self.path, self.status, self.messages)
        def _cleanup():
            for path in paths:
                if os.path.exists(path):
                    shutil.rmtree(path)
        _cleanup()
        self.addCleanup(_cleanup)
        for path in paths:
            os.makedirs(path)
        self.filepath = filepath.FilePath(self.path)
        self.checker = functools.partial(beatcheck.check, self.filepath)

    def test_empty_dir(self):
        """Test checking an empty config directory"""
        self.assertFalse(self.checker(0, 0))

    def test_no_heart(self):
        """Test checking a config directory with one file that does not beat"""
        check = {}
        jsonCheck = helper.dumps2utf8(check)
        fooFile = self.filepath.child('foo')
        fooFile.setContent(jsonCheck)
        mtime = fooFile.getModificationTime()
        self.assertFalse(self.checker(mtime, mtime))

    def test_one_check(self):
        """Test checking a config directory with one file"""
        status = os.path.join(self.status, 'foo')
        check = {'ncolony.beatcheck': {'period': 10, 'grace': 1, 'status': status}}
        jsonCheck = helper.dumps2utf8(check)
        fooFile = self.filepath.child('foo')
        fooFile.setContent(jsonCheck)
        mtime = fooFile.getModificationTime()
        self.assertFalse(self.checker(mtime, mtime))
        self.assertFalse(self.checker(mtime, mtime+9))
        self.assertEquals(self.checker(mtime, mtime+20), ['foo'])
        statusFile = filepath.FilePath(status)
        statusFile.setContent(b"111")
        newMTime = statusFile.getModificationTime()
        newMTime += 100
        ## Back...to the future
        statusFile.changed()
        os.utime(status, (newMTime, newMTime))
        self.assertFalse(self.checker(mtime, newMTime))
        self.assertFalse(self.checker(mtime, newMTime+9))
        self.assertEquals(self.checker(mtime, newMTime+11), ['foo'])

    def test_one_default_check(self):
        """Test checking a config directory with one file"""
        status = os.path.join(self.status, 'foo')
        check = {'ncolony.beatcheck': {'period': 10, 'grace': 1, 'status': self.status}}
        jsonCheck = helper.dumps2utf8(check)
        fooFile = self.filepath.child('foo')
        fooFile.setContent(jsonCheck)
        mtime = fooFile.getModificationTime()
        statusFile = filepath.FilePath(status, 'foo')
        statusFile.setContent(b"111")
        newMTime = statusFile.getModificationTime()
        newMTime += 100
        ## Back...to the future
        statusFile.changed()
        os.utime(status, (newMTime, newMTime))
        self.assertFalse(self.checker(mtime, newMTime))

    def test_grace(self):
        """Test checking that grace period is respected"""
        status = os.path.join(self.status, 'foo')
        check = {'ncolony.beatcheck': {'period': 10, 'grace': 3, 'status': status}}
        jsonCheck = helper.dumps2utf8(check)
        fooFile = self.filepath.child('foo')
        fooFile.setContent(jsonCheck)
        mtime = fooFile.getModificationTime()
        self.assertFalse(self.checker(mtime, mtime))
        self.assertFalse(self.checker(mtime, mtime+29))
        self.assertEquals(self.checker(mtime, mtime+31), ['foo'])

    def test_epoch(self):
        """Test that start time is being respected"""
        status = os.path.join(self.status, 'foo')
        check = {'ncolony.beatcheck': {'period': 10, 'grace': 1, 'status': status}}
        jsonCheck = helper.dumps2utf8(check)
        fooFile = self.filepath.child('foo')
        fooFile.setContent(jsonCheck)
        mtime = fooFile.getModificationTime()
        self.assertFalse(self.checker(mtime+100, mtime+100))
        self.assertFalse(self.checker(mtime+100, mtime+101))
        self.assertEquals(self.checker(mtime+100, mtime+111), ['foo'])

    def test_two_gone(self):
        """Test two configuration files with no status"""
        mtime = 0
        for fname in ['foo', 'bar']:
            status = os.path.join(self.status, fname)
            check = {'ncolony.beatcheck': {'period': 10, 'grace': 1, 'status': status}}
            jsonCheck = helper.dumps2utf8(check)
            fileObj = self.filepath.child(fname)
            fileObj.setContent(jsonCheck)
            mtime = max([mtime, fileObj.getModificationTime()])
        self.assertFalse(self.checker(mtime, mtime))
        self.assertEquals(set(self.checker(mtime, mtime+11)), set(['foo', 'bar']))

    def test_two_old(self):
        """Test two configuration files with old status"""
        mtime = 0
        for fname in ['foo', 'bar']:
            status = os.path.join(self.status, fname)
            check = {'ncolony.beatcheck': {'period': 10, 'grace': 1, 'status': status}}
            jsonCheck = helper.dumps2utf8(check)
            fileObj = self.filepath.child(fname)
            fileObj.setContent(jsonCheck)
            statusFile = filepath.FilePath(status)
            statusFile.setContent(b"111")
            newMTime = statusFile.getModificationTime()
            mtime = max([mtime, newMTime, fileObj.getModificationTime()])
        self.assertFalse(self.checker(mtime, mtime))
        self.assertEquals(set(self.checker(mtime, mtime+11)), set(['foo', 'bar']))

    def test_run(self):
        """Test the runner"""
        _checker_args = []
        _restarter_args = []
        def _checker(arg):
            _checker_args.append(arg)
            return ['foo', 'bar']
        def _timer():
            return 'baz'
        def _restarter(thing):
            _restarter_args.append(thing)
        beatcheck.run(_restarter, _checker, _timer)
        self.assertEquals(_checker_args, ['baz'])
        self.assertEquals(_restarter_args, ['foo', 'bar'])

    def test_make_service(self):
        """Test makeService"""
        opt = dict(config='config',
                   messages='messages',
                   freq=5)
        before = time.time()
        masterService = beatcheck.makeService(opt)
        service = masterService.getServiceNamed("beatcheck")
        after = time.time()
        self.assertIsInstance(service, tainternet.TimerService)
        self.assertEquals(service.step, 5)
        callableThing, args, kwargs = service.call
        self.assertIs(callableThing, beatcheck.run)
        self.assertFalse(kwargs)
        restarter, checker, timer = args
        self.assertIs(timer, time.time)
        self.assertIs(restarter.func, ctllib.restart)
        self.assertFalse(restarter.keywords)
        places, = restarter.args
        self.assertEquals(places, ctllib.Places(config='config', messages='messages'))
        self.assertIs(checker.func, beatcheck.check)
        self.assertFalse(checker.keywords)
        path, start = checker.args
        self.assertEquals(path.basename(), 'config')
        self.assertLessEqual(before, start)
        self.assertLessEqual(start, after)

    def test_make_service_with_health(self):
        """Test beatcheck with heart beater"""
        testWrappedHeart(self, beatcheck.makeService)

def testWrappedHeart(utest, serviceMaker):
    """Service has a child heart beater"""
    opt = dict(config='config',
               messages='messages',
               freq=5)
    test_heart.replaceEnvironment(utest)
    masterService = serviceMaker(opt)
    service = masterService.getServiceNamed('heart')
    test_heart.checkHeartService(utest, service)

class TestOptions(unittest.TestCase):

    """Test option parsing"""

    def setUp(self):
        """Set up the test"""
        self.opt = beatcheck.Options()
        self.basic = ['--message', 'message-dir', '--config', 'config-dir']

    def test_commandLine_required_messages(self):
        """Test failure on missing command line"""
        with self.assertRaises(usage.UsageError):
            self.opt.parseOptions(['--config', 'c'])

    def test_commandLine_required_config(self):
        """Test failure on missing command line"""
        with self.assertRaises(usage.UsageError):
            self.opt.parseOptions(['--message', 'm'])

    def test_basic(self):
        """Test basic command line parsing"""
        self.opt.parseOptions(self.basic)
        self.assertEqual(self.opt['messages'], 'message-dir')
        self.assertEqual(self.opt['config'], 'config-dir')
        self.assertEqual(self.opt['freq'], 10)

    def test_freq(self):
        """Test explicit freq"""
        self.opt.parseOptions(self.basic+['--freq', '13'])
        self.assertEqual(self.opt['freq'], 13)
