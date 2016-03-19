# Copyright (c) Moshe Zadka
# See LICENSE for details.

"""Check HTTP server for responsiveness"""

import collections
import functools
import json
import sys

import automat

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
               'NColony/' + ncolony.__version__ + ', '
               'Twisted/' + twisted.__version__ + ', '
               'Python ' + sys.version.replace('\n', '') + ')'
              )

_standardHeaders = client.Headers({'User-Agent': [_USER_AGENT]})

## pylint: disable=too-many-instance-attributes

class State(object):

    """State of an HTTP check"""

    KEY = 'ncolony.httpcheck'

    machine = automat.MethodicalMachine()

    def __init__(self, location, settings):
        self.location = location
        self.settings = settings
        self.content = json.dumps({})

    #### States #####
    @machine.state(serialized="initial", initial=True)
    def initial(self):
        pass # pragma: no cover

    @machine.state(serialized="closed")
    def closed(self):
        """All further inputs should error out"""
        pass # pragma: no cover

    @machine.state(serialized="hasURL")
    def hasURL(self):
        """This is a process that does not require HTTP checking

        Anything other than content_changed should error out"""
        pass # pragma: no cover

    @machine.state(serialized="inPing")
    def inPing(self):
        pass # pragma: no cover

    @machine.state(serialized="bad")
    def bad(self):
        pass # pragma: no cover

    #### Inputs #####
    @machine.input()
    def close(self):
        pass # pragma: no cover

    @machine.input()
    def readContent(self, newContent):
        pass # pragma: no cover

    @machine.input()
    def contentChanged(self):
        pass # pragma: no cover

    @machine.input()
    def gotBadReponse(self):
        pass # pragma: no cover

    @machine.input()
    def gotGoodReponse(self):
        pass # pragma: no cover

    @machine.input()
    def check(self):
        pass # pragma: no cover

    @machine.input()
    def noURL(self):
        pass # pragma: no cover

    @machine.input()
    def setURL(self, config):
        pass # pragma: no cover

    @machine.input()
    def pingStarted(self):
        pass # pragma: no cover

    @machine.input()
    def pingFinished(self):
        pass # pragma: no cover

    @machine.input()
    def setBad(self):
        pass # pragma: no cover

    #### Outputs #####
    @machine.output()
    def checkContent(self):
        newContent = self.location.getContent()
        if self.content == newContent:
            return
        self.content = newContent
        parsed = json.loads(self.content)
        if self.KEY in parsed:
            self.setURL(parsed[self.KEY])
        else:
            self.noURL()

    @machine.output()
    def genericSetURL(self, config):
        self.card = _ScoreCard(config['maxBad'])
        self.url = config['url']
        self.period = config['period']
        self.timeout = min(self.period, config['timeout'])
        self.nextCheck = self.settings.reactor.seconds() + config['grace'] * self.period

    @machine.output()
    def clearRunningCheckWithConfig(self, config):
        self.call.cancel()

    @machine.output()
    def clearRunningCheck(self):
        self.call.cancel()

    @machine.output()
    def maybeCheck(self):
        if self.settings.reactor.seconds() <= self.nextCheck:
            return
        self.pingStarted()

    @machine.output()
    def doStartPing(self):
        import sys
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
        def finishPing(dummy):
            if self.card.isBad():
                self.setBad()
            else:
                self.pingFinished()
        self.call.addCallback(finishPing)

    ### Transitions ####
    initial.upon(check, outputs=[checkContent, machine.output()(lambda self: False)], enter=initial, collector=any)
    hasURL.upon(check, outputs=[checkContent, maybeCheck, machine.output()(lambda self: False)], enter=hasURL, collector=lambda x: list(x)[1])
    bad.upon(check, outputs=[checkContent, machine.output()(lambda self: True)], enter=hasURL, collector=any)
    inPing.upon(check, outputs=[checkContent, machine.output()(lambda self: False)], enter=inPing, collector=any)

    initial.upon(close, outputs=[], enter=closed)
    inPing.upon(close, outputs=[], enter=closed)
    hasURL.upon(close, outputs=[], enter=closed)
    bad.upon(close, outputs=[], enter=closed)

    initial.upon(noURL, outputs=[], enter=initial)
    inPing.upon(noURL, outputs=[clearRunningCheck], enter=initial)
    hasURL.upon(noURL, outputs=[], enter=initial)
    bad.upon(noURL, outputs=[], enter=initial)

    inPing.upon(setURL, outputs=[clearRunningCheckWithConfig, genericSetURL], enter=hasURL)
    initial.upon(setURL, outputs=[genericSetURL], enter=hasURL)
    hasURL.upon(setURL, outputs=[genericSetURL], enter=hasURL)
    bad.upon(setURL, outputs=[genericSetURL], enter=hasURL)

    hasURL.upon(pingStarted, outputs=[doStartPing], enter=inPing)
    inPing.upon(setBad, outputs=[], enter=bad, collector=any)
    inPing.upon(pingFinished, outputs=[], enter=hasURL)

    @machine.serializer()
    def __repr__(self, state):
        return ('<%(klass)s:%(id)s:location=%(location)s,settings=%(settings)s,'
                'state=%(state)s,content=%(content)s,card=%(card)s>' %
                dict(klass=self.__class__.__name__, id=hex(id(self)),
                     location=self.location,
                     settings=self.settings,
                     state=state,
                     content=self.content,
                     card=getattr(self, 'card', None)))


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
    return [name for name, state in states.iteritems() if state.check()]

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
