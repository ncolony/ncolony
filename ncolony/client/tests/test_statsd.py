import unittest

from twisted.internet import task

from ncolony.client import statsd

class TestFormatter(unittest.TestCase):

    def setUp(self):
        self.format = statsd._format

    def test_format_incr_empty(self):
        res = self.format('hits.home', 'incr', None, None)
        self.assertEquals(res, 'hits.home:1|c')

    def test_format_incr_explicit(self):
        res = self.format('hits.home', 'incr', 3, None)
        self.assertEquals(res, 'hits.home:3|c')

    def test_format_incr_empty_prefix(self):
        res = self.format('hits.home', 'incr', None, 'froop')
        self.assertEquals(res, 'froop.hits.home:1|c')

    def test_format_incr_explicit_prefix(self):
        res = self.format('hits.home', 'incr', 2, 'froop')
        self.assertEquals(res, 'froop.hits.home:2|c')

    def test_format_decr_empty(self):
        res = self.format('hits.home', 'decr', None, None)
        self.assertEquals(res, 'hits.home:-1|c')

    def test_format_decr_explicit(self):
        res = self.format('hits.home', 'decr', 3, None)
        self.assertEquals(res, 'hits.home:-3|c')

    def test_format_decr_empty_prefix(self):
        res = self.format('hits.home', 'decr', None, 'froop')
        self.assertEquals(res, 'froop.hits.home:-1|c')

    def test_format_decr_explicit_prefix(self):
        res = self.format('hits.home', 'decr', 2, 'froop')
        self.assertEquals(res, 'froop.hits.home:-2|c')

    def test_format_timing_empty(self):
        with self.assertRaises(ValueError):
            self.format('hits.latency', 'timing', None, None)

    def test_format_timing_explicit(self):
        res = self.format('hits.latency', 'timing', 3, None)
        self.assertEquals(res, 'hits.latency:3|ms')

    def test_format_timing_empty_prefix(self):
        with self.assertRaises(ValueError):
            self.format('hits.latency', 'timing', None, 'froop')

    def test_format_timing_explicit_prefix(self):
        res = self.format('hits.latency', 'timing', 2, 'froop')
        self.assertEquals(res, 'froop.hits.latency:2|ms')

    def test_format_set_empty(self):
        with self.assertRaises(ValueError):
            self.format('hits.url', 'set', None, None)

    def test_format_set_explicit(self):
        res = self.format('hits.things', 'set', 4, None)
        self.assertEquals(res, 'hits.things:4|s')

    def test_format_set_empty_prefix(self):
        with self.assertRaises(ValueError):
            self.format('hits.things', 'set', None, 'froop')

    def test_format_set_explicit_prefix(self):
        res = self.format('hits.things', 'set', 4, 'froop')
        self.assertEquals(res, 'froop.hits.things:4|s')

    def test_format_gauge_delta_empty(self):
        with self.assertRaises(ValueError):
            self.format('hits.url', 'gaugeDelta', None, None)

    def test_format_gauge_delta_explicit(self):
        res = self.format('memory.pages', 'gaugeDelta', 4, None)
        self.assertEquals(res, 'memory.pages:+4|g')

    def test_format_gauge_delta_explicit_negative(self):
        res = self.format('memory.pages', 'gaugeDelta', -4, None)
        self.assertEquals(res, 'memory.pages:-4|g')

    def test_format_gauge_delta_empty_prefix(self):
        with self.assertRaises(ValueError):
            self.format('hits.things', 'gaugeDelta', None, 'froop')

    def test_format_gauge_delta_explicit_prefix(self):
        res = self.format('memory.pages', 'gaugeDelta', 4, 'froop')
        self.assertEquals(res, 'froop.memory.pages:+4|g')

    def test_format_gauge_set_empty(self):
        with self.assertRaises(ValueError):
            self.format('hits.url', 'gaugeSet', None, None)

    def test_format_gauge_set_explicit(self):
        res = self.format('memory.pages', 'gaugeSet', 4, None)
        self.assertEquals(res, 'memory.pages:4|g')

    def test_format_gauge_set_explicit_negative(self):
        res = self.format('memory.pages', 'gaugeSet', -4, None)
        self.assertEquals(res, 'memory.pages:0|g\nmemory.pages:-4|g')

    def test_format_gauge_set_empty_prefix(self):
        with self.assertRaises(ValueError):
            self.format('hits.things', 'gaugeSet', None, 'froop')

    def test_format_gauge_set_explicit_prefix(self):
        res = self.format('memory.pages', 'gaugeSet', 4, 'froop')
        self.assertEquals(res, 'froop.memory.pages:4|g')

class TestPipeline(unittest.TestCase):

    def setUp(self):
        def testNoLeftovers():
            delayed = self.clock.getDelayedCalls()
            self.assertEquals(list(delayed), [])
        self.addCleanup(testNoLeftovers)
        self.clock = task.Clock()

    def test_build_pipeline(self):
        write = lambda s: None
        preprocess = lambda s: s.strip()
        pipeline = statsd._Pipeline(originalWrite=write, maxsize=513, delay=0.213, reactor=self.clock, preprocess=preprocess)
        self.assertIs(pipeline.originalWrite, write)
        self.assertEquals(pipeline.maxsize, 513)
        self.assertEquals(pipeline.delay, 0.213)
        self.assertIs(pipeline.reactor, self.clock)
        self.assertIs(pipeline.preprocess, preprocess)
        self.assertEquals(pipeline.outstanding, None)
        self.assertEquals(pipeline.buffer, '')
        for attr in ('originalWrite', 'maxsize', 'delay', 'reactor', 'preprocess'):
            with self.assertRaises(AttributeError):
                setattr(pipeline, attr, getattr(pipeline, attr))

    def test_no_one_write(self):
        written = []
        preprocess = lambda s: s
        pipeline = statsd._Pipeline(originalWrite=written.append, maxsize=513, delay=0.213, reactor=self.clock, preprocess=preprocess)
        pipeline.write('hello')
        self.assertEquals(''.join(written), '')
        self.clock.advance(0.25)
        self.assertEquals(''.join(written), 'hello')

    def not_test_simple_flush(self):
        written = []
        preprocess = lambda s: s
        pipeline = statsd._Pipeline(originalWrite=written.append, maxsize=513, delay=0.213, reactor=self.clock, preprocess=preprocess)
        pipeline.write('a'*512)
        pipeline.write('b'*10)
        self.assertEquals(''.join(written), 'a'*512)
        self.clock.advance(0.3)
        self.assertEquals(''.join(written), 'a'*512+'b'*10)

## 
##     def _reallyWrite(self):
##         if self.outstanding:
##             if not self.outstanding.called:
##                 self.outstanding.cancel()
##             self.outstanding = None
##         self.original.write(preprocess(self.buffer))
##         self.buffer = ''
## 
##     def write(self, datum):
##         if len(self.buffer) + len(datum) > 0:
##             self._reallySend()
##             return
##         self.buffer += datum
##         if self.outstanding:
##             return
##         self.outstanding = reactor.callLater(delay, self._reallyWrite)
## 
## @characteristic.immutable([characteristic.Attribute('host'),
##                            characteristic.Attribute('port')])
## class _ConnectingUDPProtocol(object, protocol.DatagramProtocol):
## 
##     def __init__(self, host, port):
##         self.host = host
##         self.port = port
##         self.transport = None
## 
##     def startProtocol(self):
##         self.transport.connect(self.host, self.port)
## 
##     def write(self, data):
##         if self.transport is None:
##             return
##         self.transport.write(data)
## 
## def _preprocess(s):
##     return s.rstrip('\n')
## 
## @characteristic.immutable([characteristic.Attribute('maxsize', default_value=512),
##                            characteristic.Attribute('delay', default_value=1),
##                            characteristic.Attribute('host', default_value='127.0.0.1'),
##                            characteristic.Attribute('port', default_value=8125),
##                            characteristic.Attribute('interface', default_value='127.0.0.1'),
##                            characteristic.Attribute('reactor', None),
##                            characteristic.Attribute('prefix', ''),
##                           ])
## class Params(object):
##     pass
## 
## @characteristic.immutable([characteristic.Attribute('sender'),
##                            characteristic.Attribute('protocol')])
## class Client(object):
##     pass
## 
## def makeClient(params):
##     reactor = params.reactor
##     if params.reactor == None:
##         from twisted.internet import reactor as defaultReactor
##         reactor = defaultReactor
##     original = _ConnectingUDPProtocol(params.host, params.port)
##     pipeline = _Pipeline(original, params.maxsize, params.delay, reactor, _preprocess)
##     formatter = functools.partial(format, prefix=params.prefix)
##     sender = functools.partial(_sendToPipeline, pipeline=pipeline, randomizer=random.random, formatter=formatter)
##     return Client(sender=sender, protocol=original)
## 
## _SENDERS = []
## 
## def addClient(sender):
##     _SENDERS.append(sender)
## 
## def removeClient(sender):
##     _SENDERS.remove(sender)
## 
## def _sendToPipeline(pipeline, randomizer, formatter, stat, tp, value, prefix=None, rate=None):
##     if rate != None and rate != 1 and randomizer() < rate:
##         return
##     if prefix == None:
##         prefix = defaultPrefix
##     for formatted in _format(*args, **kwargs):
##         pipeline.write(formatted)
## 
## def sendStat(stat, tp, value=None, prefix=None, rate=None):
##     for sender in _SENDERS:
##         sender(stat=stat, tp=tp, value=value, prefix=prefix, rate=rate)
## 
## class Service(object):
## 
##     interface.implements(service.IService)
## 
##     def __init__(self, client):
##         self.client = client
## 
##     def privilegedStartService(self):
##         pass
## 
##     def startService(self):
##         addClient(self.client.sender)
##         self.port = reactor.listenUDP(0, self.client.original)
## 
##     def stopService(self):
##         removeClient(self.client.sender)
##         self.port.stopListening()
## 
##     @classmethod
##     def fromDetails(cls, **kwargs):
##         params = Params(**kwargs)
##         client = makeClient(params)
##         return cls(client)
