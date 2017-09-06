# Copyright (c) Moshe Zadka
# See LICENSE for details.

"""Tests for ncolony.httpcheck"""

import collections
import errno
import os
import shutil
import sys

import six

import twisted
from twisted.python import filepath
from twisted.internet import defer, reactor
from twisted.web import client
from twisted.application import internet as tainternet
from twisted.trial import unittest
from twisted.test import proto_helpers

import ncolony
from ncolony import httpcheck, ctllib
from ncolony.tests import test_beatcheck, helper

## pylint: disable=too-few-public-methods

class DummyHTTPAgent(object):

    """Simulate an HTTPAgent"""

    def __init__(self):
        self.pending = collections.defaultdict(list)
        self.calls = []

    def request(self, method, url, headers, body):
        """Pretend to make a request"""
        d = defer.Deferred()
        self.calls.append((method, url, headers, body))
        self.pending[url].append(d)
        return d

## pylint: enable=too-few-public-methods

def _empty(utest, path):
    def _cleanup():
        try:
            shutil.rmtree(path)
        except OSError as e:
            if e.errno != errno.ENOENT:
                raise
    _cleanup()
    utest.addCleanup(_cleanup)
    os.makedirs(path)

## pylint: disable=too-many-instance-attributes

class BaseTestHTTPChecker(unittest.TestCase):

    """Test the http checker"""

    def setUp(self):
        self.path = os.path.abspath('dummy-config')
        self.messages = os.path.abspath('dummy-messages')
        for path in (self.path, self.messages):
            _empty(self, path)
        self.filepath = filepath.FilePath(self.path)
        self.reactor = proto_helpers.MemoryReactorClock()
        self.agent = DummyHTTPAgent()
        self.settings = httpcheck.Settings(reactor=self.reactor, agent=self.agent)
        self.states = {}
        self.params = {'ncolony.httpcheck': dict(url='http://example.com/status',
                                                 period=1,
                                                 grace=1,
                                                 maxBad=0,
                                                 timeout=1)}

## pylint: enable=too-many-instance-attributes

class TestState(BaseTestHTTPChecker):

    """Tests for State class"""

    def setUp(self):
        BaseTestHTTPChecker.setUp(self)
        self.location = self.filepath.child('foo')
        self.state = httpcheck.State(self.location, self.settings)

    def test_repr(self):
        """Repr includes everything"""
        self.location.setContent(helper.dumps2utf8(self.params))
        self.assertFalse(self.state.check())
        s = repr(self.state)
        cardS = repr(self.state.card)
        self.assertEquals(cardS[0], '<')
        self.assertEquals(cardS[-1], '>')
        cardS = cardS[1:-1]
        parts = cardS.split(':')
        self.assertEquals(len(parts), 3)
        values = dict(x.split('=') for x in parts[-1].split(','))
        self.assertEquals(values.pop('bad'), '0')
        self.assertEquals(values.pop('maxBad'), '0')
        self.assertEquals(values, {})
        self.assertIn(cardS, s)
        self.assertEquals(s[0], '<')
        self.assertEquals(s[-1], '>')
        s = s[1:-1]
        s = s.replace(cardS, '')
        parts = s.split(':', 2)
        self.assertEquals(len(parts), 3)
        values = parts[2]
        for portion in ('card=<>', 'call=None', 'closed=False', 'settings='+repr(self.settings),
                        'location='+repr(self.location)):
            self.assertIn(portion, values)
            values = values.replace(portion, '')
        values = values.strip(',')
        name, value = values.split('=', 1)
        self.assertEquals(name, 'content')
        ## pylint: disable=eval-used
        self.assertEquals(eval(value), self.params)
        ## pylint: enable=eval-used

    def test_no_check(self):
        """Checking an empty state results in success"""
        self.location.setContent(helper.dumps2utf8({}))
        self.reactor.advance(3)
        self.assertFalse(self.state.check())

    def test_bad_check(self):
        """Checking unsuccessful HTTP results in failure"""
        self.location.setContent(helper.dumps2utf8(self.params))
        self.assertFalse(self.state.check())
        self.reactor.advance(3)
        self.assertFalse(self.state.check())
        self.reactor.advance(3)
        self.assertTrue(self.state.check())
        error, = self.flushLoggedErrors()
        error.trap(defer.CancelledError)

    def test_close_after_check(self):
        """Closing state"""
        self.location.setContent(helper.dumps2utf8(self.params))
        self.assertFalse(self.state.check())
        self.reactor.advance(3)
        self.assertFalse(self.state.check())
        self.state.close()
        self.assertTrue(self.state.closed)
        error, = self.flushLoggedErrors()
        error.trap(defer.CancelledError)

    def test_reset_after_check(self):
        """Closing state"""
        self.location.setContent(helper.dumps2utf8(self.params))
        self.assertFalse(self.state.check())
        self.reactor.advance(3)
        self.assertFalse(self.state.check())
        params = {}
        self.location.setContent(helper.dumps2utf8(params))
        self.assertFalse(self.state.check())
        error, = self.flushLoggedErrors()
        error.trap(defer.CancelledError)
        self.assertIsNone(self.state.call)

    def test_good_check(self):
        """Checking successful HTTP results in success"""
        self.location.setContent(helper.dumps2utf8(self.params))
        self.assertFalse(self.state.check())
        self.reactor.advance(3)
        self.assertFalse(self.state.check())
        (method, gotUrl, headers, body), = self.agent.calls
        self.assertIsNone(body)
        self.assertEquals(method, 'GET')
        url = next(six.itervalues(self.params))['url']
        self.assertEquals(url, gotUrl)
        self.assertIsInstance(headers, client.Headers)
        userAgent, = headers.getRawHeaders('user-agent')
        self.assertIn('Twisted/' + twisted.__version__, userAgent)
        self.assertIn('NColony/' + str(ncolony.__version__), userAgent)
        self.assertIn('Python ' + sys.version.replace('\n', ''), userAgent)
        d, = self.agent.pending[url]
        d.callback(client.Response(('HTTP', 1, 1), 200, 'OK', None, None))
        self.assertFalse(self.state.check())
        self.assertLessEqual(len(self.agent.calls), 1)

    def test_close(self):
        """Checking closing causes APIs to error out"""
        self.state.close()
        with self.assertRaises(ValueError):
            self.state.close()
        with self.assertRaises(ValueError):
            self.state.check()


class TestCheck(BaseTestHTTPChecker):

    """Test the check function"""

    def setUp(self):
        BaseTestHTTPChecker.setUp(self)
        self.location = self.filepath.child('foo')
        self.location.createDirectory()
        self.states = {}

    def test_check_empty(self):
        """empty directory causes empty states"""
        ret = httpcheck.check(self.settings, self.states, self.location)
        self.assertEquals(ret, [])
        self.assertEquals(self.states, {})

    def test_check_simplestate(self):
        """one configuration in directory is checked"""
        self.location.child('child').setContent(helper.dumps2utf8(self.params))
        ret = httpcheck.check(self.settings, self.states, self.location)
        self.assertEquals(ret, [])
        (name, state), = six.iteritems(self.states)
        self.assertEquals(name, 'child')
        httpcheck.check(self.settings, self.states, self.location)
        self.assertEquals(ret, [])
        self.reactor.advance(3)
        httpcheck.check(self.settings, self.states, self.location)
        self.reactor.advance(3)
        ret = httpcheck.check(self.settings, self.states, self.location)
        bad, = ret
        err, = self.flushLoggedErrors()
        err.trap(defer.CancelledError)
        self.assertEquals(bad, 'child')
        self.location.child('child').remove()
        ret = httpcheck.check(self.settings, self.states, self.location)
        self.assertEquals(ret, [])
        self.assertTrue(state.closed)
        self.assertEquals(self.states, {})

    def test_run(self):
        """run restarts each bad thing"""
        l = []
        restarter = l.append
        check = lambda: [1, 2, 3]
        httpcheck.run(restarter, check)
        self.assertEquals(l, [1, 2, 3])

    def test_make_service(self):
        """Test makeService"""
        opt = dict(config='config',
                   messages='messages',
                   freq=5)
        masterService = httpcheck.makeService(opt)
        service = masterService.getServiceNamed("httpcheck")
        self.assertIsInstance(service, tainternet.TimerService)
        self.assertEquals(service.step, 5)
        callableThing, args, kwargs = service.call
        self.assertIs(callableThing, httpcheck.run)
        self.assertFalse(kwargs)
        restarter, checker = args
        self.assertIs(restarter.func, ctllib.restart)
        self.assertFalse(restarter.keywords)
        places, = restarter.args
        self.assertEquals(places, ctllib.Places(config='config', messages='messages'))
        self.assertIs(checker.func, httpcheck.check)
        self.assertFalse(checker.keywords)
        settings, states, location = checker.args
        self.assertEquals(location, filepath.FilePath(opt['config']))
        self.assertEquals(states, {})
        self.assertIs(settings.reactor, reactor)
        agent = settings.agent
        self.assertIsInstance(agent, client.Agent)
        ## pylint: disable=protected-access
        self.assertTrue(agent._pool.persistent)
        ## pylint: enable=protected-access

    def test_make_service_with_health(self):
        """Test httpcheck with heart beater"""
        test_beatcheck.testWrappedHeart(self, httpcheck.makeService)
