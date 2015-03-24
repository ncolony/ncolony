# Copyright (c) Moshe Zadka
# See LICENSE for details.
"""Test ncolony.statsd"""

import time
import unittest

from zope.interface import verify

from twisted.python import usage
from twisted.internet import protocol as tiprotocol, task as titask
from twisted.application import service as taservice, internet as tainternet

from ncolony import statsd
from ncolony.client.tests import test_heart

class TestGetSamples(unittest.TestCase):

    """Test the getStatsdSamples function"""

    def _dataCompare(self, packet, expected):
        got = list(statsd.getStatsdSamples(packet))
        self.assertEquals(got, expected)

    def test_simple_gauge(self):
        """Test gauge parsing"""
        self._dataCompare('foo:2|g',
                          [statsd.Sample(meaning='gauge', key='foo', fields=['2']),
                          ])

    def test_simple_counter(self):
        """Test simple counter parsing"""
        self._dataCompare('foo:2|c',
                          [statsd.Sample(meaning='counter', key='foo', fields=['2']),
                          ])

    def test_simple_timer(self):
        """Test simple timer parsing"""
        self._dataCompare('foo:2|ms',
                          [statsd.Sample(meaning='timer', key='foo', fields=['2']),
                          ])

    def test_simple_set(self):
        """Test set parsing"""
        self._dataCompare('foo:2|s',
                          [statsd.Sample(meaning='set', key='foo', fields=['2']),
                          ])

    def test_multiline_set(self):
        """Test two sets on separate lines parsing"""
        self._dataCompare('foo:2|s\nbar:3|s',
                          [statsd.Sample(meaning='set', key='foo', fields=['2']),
                           statsd.Sample(meaning='set', key='bar', fields=['3']),
                          ])

    def test_ignore_spaces(self):
        """Test spaces are ignored"""
        self._dataCompare(' foo:2|s \nbar:3|s',
                          [statsd.Sample(meaning='set', key='foo', fields=['2']),
                           statsd.Sample(meaning='set', key='bar', fields=['3']),
                          ])

    def test_ignore_empty_lines(self):
        """Test empty lines are ignored"""
        self._dataCompare(' foo:2|s \n   \nbar:3|s',
                          [statsd.Sample(meaning='set', key='foo', fields=['2']),
                           statsd.Sample(meaning='set', key='bar', fields=['3']),
                          ])

    def test_multi_sample(self):
        """Test a key with several metrics"""
        self._dataCompare('foo:2|s:3|g',
                          [statsd.Sample(meaning='set', key='foo', fields=['2']),
                           statsd.Sample(meaning='gauge', key='foo', fields=['3']),
                          ])

    def test_default_zero(self):
        """Test the default is 0"""
        self._dataCompare('foo:|g',
                          [statsd.Sample(meaning='gauge', key='foo', fields=['0']),
                          ])

    def test_error_not_enough_fields(self):
        """Test not sending a value field raises an error"""
        with self.assertRaises(ValueError):
            self._dataCompare('foo:2g', [])

    def test_space_key(self):
        """Test spaces in keys become underscores"""
        self._dataCompare('fo  o:|g',
                          [statsd.Sample(meaning='gauge', key='fo_o', fields=['0']),
                          ])

    def test_slash_key(self):
        """Test slashes in keys become periods"""
        self._dataCompare('fo/o:|g',
                          [statsd.Sample(meaning='gauge', key='fo.o', fields=['0']),
                          ])

    def test_invalid_characters(self):
        """Test invalid characters in keys are ignored"""
        self._dataCompare('fo#o:|g\nfo@o:|g\nfo%o:|g\nfo1o:|g\nFOO:|g',
                          [statsd.Sample(meaning='gauge', key='foo', fields=['0']),
                           statsd.Sample(meaning='gauge', key='foo', fields=['0']),
                           statsd.Sample(meaning='gauge', key='foo', fields=['0']),
                           statsd.Sample(meaning='gauge', key='fo1o', fields=['0']),
                           statsd.Sample(meaning='gauge', key='FOO', fields=['0']),
                          ])


class TestStatsStore(unittest.TestCase):

    """Test the Store class"""

    def setUp(self):
        self.store = statsd.Store(0)

    def _getAll(self, now):
        return list(self.store.getAndReset(now))

    def test_add_simple_counter(self):
        """Test updating with a simple counter"""
        self.store.update(statsd.Sample('counter', 'foo', ['1']))
        allThings = self._getAll(2)
        self.assertEquals(allThings,
                          [statsd.Summary(category='counters', key='foo.count', value=1),
                           statsd.Summary(category='counters', key='foo.rate', value=0.5),
                          ])
        allThings = self._getAll(2)
        self.assertFalse(allThings)

    def test_add_float_counter(self):
        """Test updating with a non-integer counter"""
        self.store.update(statsd.Sample('counter', 'foo', ['1.5']))
        allThings = self._getAll(2)
        self.assertEquals(allThings,
                          [statsd.Summary(category='counters', key='foo.count', value=1.5),
                           statsd.Summary(category='counters', key='foo.rate', value=0.75),
                          ])
        allThings = self._getAll(2)
        self.assertFalse(allThings)

    def test_add_float_rate_counter(self):
        """Test updating with a counter with non-integer rate"""
        self.store.update(statsd.Sample('counter', 'foo', ['1', '@0.5']))
        allThings = self._getAll(1)
        self.assertEquals(allThings,
                          [statsd.Summary(category='counters', key='foo.count', value=2),
                           statsd.Summary(category='counters', key='foo.rate', value=2),
                          ])
        allThings = self._getAll(2)
        self.assertFalse(allThings)

    def test_add_rate_counter(self):
        """Test updating with a counter with rate"""
        self.store.update(statsd.Sample('counter', 'foo', ['1', '@2']))
        allThings = self._getAll(1)
        self.assertEquals(allThings,
                          [statsd.Summary(category='counters', key='foo.count', value=0.5),
                           statsd.Summary(category='counters', key='foo.rate', value=0.5),
                          ])
        allThings = self._getAll(2)
        self.assertFalse(allThings)

    def test_add_ignored_rate_counter(self):
        """Test updating with a counter with invalid rate, that should be ignored"""
        self.store.update(statsd.Sample('counter', 'foo', ['1', '%2']))
        allThings = self._getAll(1)
        self.assertEquals(allThings,
                          [statsd.Summary(category='counters', key='foo.count', value=1),
                           statsd.Summary(category='counters', key='foo.rate', value=1),
                          ])
        allThings = self._getAll(2)
        self.assertFalse(allThings)

    def test_add_simple_counter_twice(self):
        """Test updating with a counter twice (should add values)"""
        self.store.update(statsd.Sample('counter', 'foo', ['1']))
        self.store.update(statsd.Sample('counter', 'foo', ['1']))
        allThings = self._getAll(2)
        self.assertEquals(allThings,
                          [statsd.Summary(category='counters', key='foo.count', value=2),
                           statsd.Summary(category='counters', key='foo.rate', value=1),
                          ])
        allThings = self._getAll(2)
        self.assertFalse(allThings)

    def test_add_float_gauge(self):
        """Test non-integer gauge"""
        self.store.update(statsd.Sample('gauge', 'foo', ['1.3']))
        allThings = self._getAll(1)
        self.assertEquals(allThings,
                          [statsd.Summary(category='gauges', key='foo', value=1.3),
                          ])

    def test_add_gauge(self):
        """Test two gauges"""
        self.store.update(statsd.Sample('gauge', 'foo', ['1']))
        self.store.update(statsd.Sample('gauge', 'bar', ['3']))
        allThings = self._getAll(1)
        self.assertEquals(set(allThings),
                          set([statsd.Summary(category='gauges', key='foo', value=1),
                               statsd.Summary(category='gauges', key='bar', value=3),
                              ]))
        allThings = self._getAll(1)
        self.assertEquals(set(allThings),
                          set([statsd.Summary(category='gauges', key='foo', value=1),
                               statsd.Summary(category='gauges', key='bar', value=3),
                              ]))
        self.store.update(statsd.Sample('gauge', 'foo', ['+1']))
        allThings = self._getAll(1)
        self.assertEquals(set(allThings),
                          set([statsd.Summary(category='gauges', key='foo', value=2),
                               statsd.Summary(category='gauges', key='bar', value=3),
                              ]))
        self.store.update(statsd.Sample('gauge', 'foo', ['-2']))
        allThings = self._getAll(1)
        self.assertEquals(set(allThings),
                          set([statsd.Summary(category='gauges', key='foo', value=0),
                               statsd.Summary(category='gauges', key='bar', value=3),
                              ]))
        self.store.update(statsd.Sample('gauge', 'foo', ['+1']))
        self.store.update(statsd.Sample('gauge', 'foo', ['4']))
        allThings = self._getAll(1)
        self.assertEquals(set(allThings),
                          set([statsd.Summary(category='gauges', key='foo', value=4),
                               statsd.Summary(category='gauges', key='bar', value=3),
                              ]))

    def test_add_set(self):
        """Test add several set items"""
        self.store.update(statsd.Sample('set', 'foo', ['hello']))
        self.store.update(statsd.Sample('set', 'foo', ['goodbye']))
        self.store.update(statsd.Sample('set', 'foo', ['hello']))
        allThings = self._getAll(1)
        self.assertEquals(allThings,
                          [statsd.Summary(category='sets', key='foo.count', value=2),
                          ])
        allThings = self._getAll(2)
        self.assertFalse(allThings)

    def test_add_simple_timer(self):
        """Test add simple timer values"""
        for dummy in range(9):
            self.store.update(statsd.Sample('timer', 'foo', ['1']))
        self.store.update(statsd.Sample('timer', 'foo', ['2']))
        allThings = self._getAll(2)
        self.assertEquals(set(allThings),
                          set([statsd.Summary(category='timers', key='foo.mean', value=1),
                               statsd.Summary(category='timers', key='foo.upper', value=2),
                               statsd.Summary(category='timers', key='foo.upper_90', value=1),
                               statsd.Summary(category='timers', key='foo.lower', value=1),
                               statsd.Summary(category='timers', key='foo.count', value=10),
                               statsd.Summary(category='timers', key='foo.count_ps', value=5),
                              ]))

    def test_add_simple_timer_one_value(self):
        """Test timers with one value"""
        self.store.update(statsd.Sample('timer', 'foo', ['1']))
        allThings = self._getAll(2)
        self.assertEquals(set(allThings),
                          set([statsd.Summary(category='timers', key='foo.mean', value=1),
                               statsd.Summary(category='timers', key='foo.upper', value=1),
                               statsd.Summary(category='timers', key='foo.upper_90', value=1),
                               statsd.Summary(category='timers', key='foo.lower', value=1),
                               statsd.Summary(category='timers', key='foo.count', value=1),
                               statsd.Summary(category='timers', key='foo.count_ps', value=0.5),
                              ]))

    def test_add_twenty_timers_with_outliers(self):
        """Test twenty timers with two outliers"""
        for dummy in range(18):
            self.store.update(statsd.Sample('timer', 'foo', ['1']))
        for dummy in range(2):
            self.store.update(statsd.Sample('timer', 'foo', ['2']))
        allThings = self._getAll(2)
        self.assertEquals(set(allThings),
                          set([statsd.Summary(category='timers', key='foo.mean', value=1),
                               statsd.Summary(category='timers', key='foo.upper', value=2),
                               statsd.Summary(category='timers', key='foo.upper_90', value=1),
                               statsd.Summary(category='timers', key='foo.lower', value=1),
                               statsd.Summary(category='timers', key='foo.count', value=20),
                               statsd.Summary(category='timers', key='foo.count_ps', value=10),
                              ]))

    def test_add_interesting_mean(self):
        """Test non-trivial mean"""
        self.store.update(statsd.Sample('timer', 'foo', ['100'])) ## outlier
        for dummy in range(4):
            self.store.update(statsd.Sample('timer', 'foo', ['3']))
        for dummy in range(4):
            self.store.update(statsd.Sample('timer', 'foo', ['1']))
        self.store.update(statsd.Sample('timer', 'foo', ['2']))
        allThings = self._getAll(2)
        self.assertEquals(set(allThings),
                          set([statsd.Summary(category='timers', key='foo.mean', value=2),
                               statsd.Summary(category='timers', key='foo.upper', value=100),
                               statsd.Summary(category='timers', key='foo.upper_90', value=3),
                               statsd.Summary(category='timers', key='foo.lower', value=1),
                               statsd.Summary(category='timers', key='foo.count', value=10),
                               statsd.Summary(category='timers', key='foo.count_ps', value=5),
                              ]))


class TestParsingStoreProtocol(unittest.TestCase):

    """Test UDPProtocol"""

    def setUp(self):
        self.data = []
        self.results = []
        self.updated = []
        def _parse(data):
            self.data.append(data)
            return iter(self.results)
        def _update(summary):
            self.updated.append(summary)
        self.protocol = statsd.UDPProtocol(update=_update, parse=_parse)

    def test_interface(self):
        """Test it's a datagram protocol"""
        self.assertIsInstance(self.protocol, tiprotocol.DatagramProtocol)

    def test_no_call_at_beginning(self):
        """Test no updates in the beginning"""
        self.assertFalse(self.data)
        self.assertFalse(self.updated)

    def test_datagram_received_no_results(self):
        """Test ignoring non-successful parsing"""
        contents = 'hello'
        self.protocol.datagramReceived(contents, None)
        self.assertEquals(self.data, ['hello'])
        self.assertFalse(self.updated)

    def test_datagram_received_two_results(self):
        """Test getting two results"""
        contents = 'hello'
        self.results = [1, 2]
        self.protocol.datagramReceived(contents, None)
        self.assertEquals(self.data, ['hello'])
        self.assertEquals(self.updated, [1, 2])

## pylint: disable=too-few-public-methods

class TestPublish(unittest.TestCase):

    """Test publish()"""

    def test_publisher_simple(self):
        """Test publish()"""
        prefix = 'hello'
        times = []
        published = []
        def _getSummaries(now):
            times.append(now)
            return [statsd.Summary(category='counters', key='foo.bar', value=5),
                    statsd.Summary(category='gauges', key='foo.baz', value=2.3),
                   ]
        def _timer():
            return 'tic'
        def _publish(metric):
            published.append(metric)
        statsd.publish(prefix, _getSummaries, _publish, _timer)
        self.assertEquals(times, ['tic'])
        self.assertEquals(published, [statsd.Metrics('hello.counters.foo.bar', 5, 'tic'),
                                      statsd.Metrics('hello.gauges.foo.baz', 2.3, 'tic')])

class _DummyFactory(object):

    def __init__(self):
        self.clients = []

    def clientConnectionMade(self, protocol):
        """pretend to make a connection"""
        self.clients.append(protocol)

class _DummyTransport(object):

    def __init__(self):
        self.output = ''

    def write(self, stuff):
        """pretend to write"""
        self.output += stuff

class _DummyProtocol(object):

    def __init__(self):
        self.metrics = []

    def sendMetrics(self, metrics):
        """pretend to sendMetrics"""
        self.metrics.extend(metrics)

class _DummyConnector(object):

    connections = 0

    def connect(self):
        """pretend to connect"""
        self.connections += 1

## pylint: enable=too-few-public-methods

class TestCarbonTextProtocol(unittest.TestCase):

    """Test CarbonTextProtocol"""

    def setUp(self):
        self.protocol = statsd.CarbonTextProtocol()
        self.factory = _DummyFactory()
        self.transport = _DummyTransport()
        self.protocol.factory = self.factory
        self.protocol.transport = self.transport

    def test_interface(self):
        """Test it's a protocol"""
        self.assertIsInstance(self.protocol, tiprotocol.Protocol)

    def test_connectionMade(self):
        """Test connectionMade"""
        self.protocol.connectionMade()
        client, = self.factory.clients
        self.assertIs(client, self.protocol)

    def test_sendMetrics(self):
        """Test sendMetrics"""
        metrics = [statsd.Metrics('hello.counters.foo.bar', 5, 10),
                   statsd.Metrics('hello.gauges.foo.baz', 2.3, 10)]
        self.protocol.sendMetrics(metrics)
        self.assertEquals(self.transport.output,
                          'hello.counters.foo.bar 5 10\nhello.gauges.foo.baz 2.3 10\n')

class TestMetricsSendingFactory(unittest.TestCase):

    """Test MetricsSendingFactory"""

    def setUp(self):
        self.factory = statsd.MetricsSendingFactory(_DummyProtocol)
        self.factory.clock = titask.Clock()
        self.protocol = self.factory.buildProtocol(None)
        self.connector = _DummyConnector()
        self.reason = object()

    def test_interface(self):
        """Test subclassing from ReconnectingClientFactory"""
        self.assertIsInstance(self.factory, tiprotocol.ReconnectingClientFactory)

    def test_clientConnectionLost(self):
        """Test clientConnectionLost method"""
        self.factory.clientConnectionMade(self.protocol)
        self.factory.clientConnectionLost(self.connector, self.reason)
        self.assertIsNone(self.factory.proto)
        self.factory.clock.advance(10)
        self.assertEquals(self.connector.connections, 1)

    def test_clientConnectionFailed(self):
        """Test clientConnectionFailed method"""
        self.factory.clientConnectionMade(self.protocol)
        self.factory.clientConnectionFailed(self.connector, self.reason)
        self.assertIsNone(self.factory.proto)
        self.factory.clock.advance(10)
        self.assertEquals(self.connector.connections, 1)

    def test_clientConnectionMade(self):
        """Test clientConnectionMade method"""
        self.factory.clientConnectionMade(self.protocol)
        self.assertIs(self.factory.proto, self.protocol)

    def test_sendMetrics_connected(self):
        """Test metric sending while connected"""
        self.factory.clientConnectionMade(self.protocol)
        metrics = [statsd.Metrics('hello.counters.foo.bar', 5, 10),
                   statsd.Metrics('hello.gauges.foo.baz', 2.3, 10)]
        self.factory.sendMetrics(metrics)
        self.assertEquals(metrics, self.protocol.metrics)

    def test_sendMetrics_disconnected(self):
        """Test metric sending while disconnected, and then connecting"""
        metrics = [statsd.Metrics('hello.counters.foo.bar', 5, 10),
                   statsd.Metrics('hello.gauges.foo.baz', 2.3, 10)]
        self.factory.sendMetrics(metrics)
        self.factory.clientConnectionMade(self.protocol)
        self.assertEquals(metrics, self.protocol.metrics)

## pylint: disable=no-member
TCPClient, UDPServer = tainternet.TCPClient, tainternet.UDPServer
## pylint: enable=no-member

class TestPluginStuff(unittest.TestCase):

    """Test the things needed to enable writing the twistd plugin"""

    def setUp(self):
        self.options = statsd.Options()
        self.basicOptions = ['--prefix=here', '--carbon-host=carbon.example.net']

    def test_opt_required(self):
        """Test required values for options"""
        for option in self.basicOptions:
            parser = statsd.Options()
            optionRemoved = [opt for opt in self.basicOptions if opt != option]
            with self.assertRaises(usage.UsageError):
                parser.parseOptions(optionRemoved)

    def test_opt_default(self):
        """Test default values for options"""
        self.options.parseOptions(self.basicOptions)
        opt = self.options
        self.assertEquals(opt['interface'], '127.0.0.1')
        self.assertEquals(opt['port'], 8125)
        self.assertEquals(opt['carbon-port'], 2003)
        self.assertEquals(opt['frequency'], 60)
        self.assertEquals(opt['prefix'], 'here')
        self.assertEquals(opt['carbon-host'], 'carbon.example.net')

    def test_opt_full(self):
        """Test giving all options non-default values"""
        full = self.basicOptions + ['--interface=0.0.0.0', '--port=8123',
                                    '--carbon-host=carbon.example.com', '--carbon-port=2004',
                                    '--frequency=62', '--prefix=foo',
                                   ]
        self.options.parseOptions(full)
        opt = self.options
        self.assertEquals(opt['interface'], '0.0.0.0')
        self.assertEquals(opt['port'], 8123)
        self.assertEquals(opt['carbon-port'], 2004)
        self.assertEquals(opt['frequency'], 62)
        self.assertEquals(opt['prefix'], 'foo')
        self.assertEquals(opt['carbon-host'], 'carbon.example.com')

    def test_service_making(self):
        """Test makeService"""
        opt = {'interface': '127.0.0.1', 'port': 8111,
               'carbon-host': 'carbon.example.org', 'carbon-port': 1111,
               'prefix': 'localhost.localdomain', 'freq': 63,
              }
        before = time.time()
        service = statsd.makeService(opt)
        after = time.time()
        verify.verifyObject(taservice.IServiceCollection, service)
        verify.verifyObject(taservice.IService, service)
        store = self._check_statsd_subservice(service, opt)
        self.assertLessEqual(before, store.lastNow)
        self.assertLessEqual(store.lastNow, after)
        factory = self._check_carbon_subservice(service, opt)
        self._check_publisher_subservice(service, opt, factory, store)

    def test_service_making_with_health(self):
        """Test makeService"""
        opt = {'interface': '127.0.0.1', 'port': 8111,
               'carbon-host': 'carbon.example.org', 'carbon-port': 1111,
               'prefix': 'localhost.localdomain', 'freq': 63,
              }
        myEnv = test_heart.buildEnv()
        test_heart.replaceEnvironment(self, myEnv)
        service = statsd.makeService(opt)
        myHeart = service.getServiceNamed('heart')
        test_heart.checkHeartService(self, myHeart)

    def _check_publisher_subservice(self, service, opt, factory, store):
        publisher = service.getServiceNamed('publisher')
        self.assertIsInstance(publisher, tainternet.TimerService)
        self.assertEquals(publisher.step, opt['freq'])
        function, args, kwargs = publisher.call
        self.assertFalse(kwargs)
        self.assertIs(function, statsd.publish)
        prefix, getSummaries, sendMetrics, timer = args
        self.assertIs(timer, time.time)
        self.assertEquals(prefix, opt['prefix'])
        self.assertIs(getSummaries.im_self, store)
        self.assertIs(getSummaries.im_func, store.getAndReset.im_func)
        self.assertIs(sendMetrics.im_self, factory)
        self.assertIs(sendMetrics.im_func, factory.sendMetrics.im_func)

    def _check_carbon_subservice(self, service, opt):
        carbon = service.getServiceNamed('carbon')
        self.assertIsInstance(carbon, TCPClient)
        args, kwargs = carbon.args, carbon.kwargs
        self.assertFalse(args)
        factory = kwargs.pop('factory')
        self.assertEquals(kwargs, dict(host=opt['carbon-host'], port=opt['carbon-port']))
        self.assertIsInstance(factory, statsd.MetricsSendingFactory)
        self.assertIs(factory.protocol, statsd.CarbonTextProtocol)
        return factory

    def _check_statsd_subservice(self, service, opt):
        statsdSer = service.getServiceNamed('statsd')
        self.assertIsInstance(statsdSer, UDPServer)
        args, kwargs = statsdSer.args, statsdSer.kwargs
        self.assertFalse(args)
        protocol = kwargs.pop('protocol')
        self.assertEquals(kwargs, dict(interface=opt['interface'], port=opt['port']))
        self.assertIsInstance(protocol, statsd.UDPProtocol)
        update, parse = protocol.update, protocol.parse
        store = update.im_self
        self.assertIs(parse, statsd.getStatsdSamples)
        self.assertIs(update.im_func, statsd.Store(None).update.im_func)
        self.assertIsInstance(store, statsd.Store)
        return store
