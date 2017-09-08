# Copyright (c) Moshe Zadka
# See LICENSE for details.

"""Check HTTP server for responsiveness"""

import collections
import functools
import json
import sys

import six

import twisted

from twisted.application import internet as tainternet
from twisted.internet import defer, reactor
from twisted.web import client

import ncolony
from ncolony import beatcheck
from ncolony.client import heart

class _ScoreCard(object):

    def __init__(self, maxBad=0):
        self.maxBad = maxBad
        self.bad = 0

    def isBad(self):
        """Too many unsuccessful checks"""
        return self.bad > self.maxBad

    def markBad(self, dummyValue):
        """Note an unsuccessful check"""
        self.bad += 1

    def markGood(self, dummyValue):
        """Note a successful check"""
        self.bad = 0

    def __repr__(self):
        return ('<%(klass)s:%(id)s:maxBad=%(maxBad)s,bad=%(bad)s>' %
                dict(klass=self.__class__.__name__,
                     id=hex(id(self)),
                     maxBad=self.maxBad,
                     bad=self.bad))

Settings = collections.namedtuple('Settings', 'reactor agent')

_USER_AGENT = ('NColony HTTP Check ('
               'NColony/' + str(ncolony.__version__) + ', '
               'Twisted/' + twisted.__version__ + ', '
               'Python ' + sys.version.replace('\n', '') + ')'
              )

_standardHeaders = client.Headers({'User-Agent': [_USER_AGENT]})

## pylint: disable=too-many-instance-attributes

class State(object):

    """State of an HTTP check"""

    KEY = 'ncolony.httpcheck'

    def __init__(self, location, settings):
        self.location = location
        self.settings = settings
        self.closed = False
        self.content = None
        self.call = None
        self.card = None
        self.url = None
        self.nextCheck = None
        self.period = None
        self.timeout = None

    def __repr__(self):
        return ('<%(klass)s:%(id)s:location=%(location)s,settings=%(settings)s,'
                'closed=%(closed)s,content=%(content)s,call=%(call)s,card=%(card)s>' %
                dict(klass=self.__class__.__name__, id=hex(id(self)),
                     location=self.location,
                     settings=self.settings,
                     closed=self.closed,
                     content=self.content,
                     call=self.call,
                     card=self.card))

    def _reset(self):
        self.content = None
        self._maybeReset()

    def close(self):
        """Discard data and cancel all calls.

        Instance cannot be reused after closing.
        """
        if self.closed:
            raise ValueError("Cannot close a closed state")
        if self.call is not None:
            self.call.cancel()
        self.closed = True

    def check(self):
        """Check the state of HTTP"""
        if self.closed:
            raise ValueError("Cannot check a closed state")
        self._maybeReset()
        if self.url is None:
            return False
        return self._maybeCheck()

    def _maybeReset(self):
        content = self.location.getContent().decode('utf-8')
        if content == self.content:
            return
        self.content = content
        if self.call is not None:
            self.call.cancel()
            self.call = None
        parsed = json.loads(self.content)
        config = parsed.get(self.KEY)
        if config is None:
            self.url = None
            self.card = _ScoreCard()
            return
        self.url = config['url']
        self.period = config['period']
        self.card = _ScoreCard(config['maxBad'])
        self.timeout = min(self.period, config['timeout'])
        self.nextCheck = self.settings.reactor.seconds() + config['grace'] * self.period

    def _maybeCheck(self):
        if self.settings.reactor.seconds() <= self.nextCheck:
            return False
        assert self.call is None, 'Timeout reached, call still outstanding'
        if self.card.isBad():
            self._reset()
            return True
        self.nextCheck = self.settings.reactor.seconds() + self.period
        self.call = self.settings.agent.request('GET', self.url, _standardHeaders, None)
        delayedCall = self.settings.reactor.callLater(self.timeout, self.call.cancel)
        def _gotResult(result):
            if delayedCall.active():
                delayedCall.cancel()
            return result
        self.call.addBoth(_gotResult)
        self.call.addErrback(defer.logError)
        self.call.addCallbacks(callback=self.card.markGood, errback=self.card.markBad)
        def _removeCall(dummy):
            self.call = None
        self.call.addCallback(_removeCall)
        return False

## pylint: enable=too-many-instance-attributes

def check(settings, states, location):
    """Check all processes"""
    children = {child.basename() : child for child in location.children()}
    last = set(states)
    current = set(children)
    gone = last - current
    added = current - last
    for name in gone:
        states[name].close()
        del states[name]
    for name in added:
        states[name] = State(location=children[name], settings=settings)
    return [name for name, state in six.iteritems(states) if state.check()]

def run(restarter, checker):
    """Run restarter on the checker's output

    :params restarter: something to run on the output of the checker
    :params checker: a function expected to get one argument (current time)
                     and return a list of stale names
    :params timer: a function of zero arguments, intended to return current time
    :returns: None
    """
    for bad in checker():
        restarter(bad)

def makeService(opt):
    """Make a service

    :params opt: dictionary-like object with 'freq', 'config' and 'messages'
    :returns: twisted.application.internet.TimerService that at opt['freq']
              checks for stale processes in opt['config'], and sends
              restart messages through opt['messages']
    """
    restarter, path = beatcheck.parseConfig(opt)
    pool = client.HTTPConnectionPool(reactor)
    agent = client.Agent(reactor=reactor, pool=pool)
    settings = Settings(reactor=reactor, agent=agent)
    states = {}
    checker = functools.partial(check, settings, states, path)
    httpcheck = tainternet.TimerService(opt['freq'], run, restarter, checker)
    httpcheck.setName('httpcheck')
    return heart.wrapHeart(httpcheck)

Options = beatcheck.Options
