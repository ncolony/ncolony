# Copyright (c) Moshe Zadka
# See LICENSE for details.

"""ncolony.statsd
==================

A StatsD clone.

Provides a twistd plug-in that implements the statsd protocol,
and sends aggregate statistics to Graphite Carbon.
"""

from __future__ import division

import collections
import math
import string
import time

from twisted.python import usage
from twisted.internet import protocol as tiprotocol
from twisted.application import service, internet as tainternet

from ncolony import heart

Sample = collections.namedtuple('Sample', 'meaning key fields')
Summary = collections.namedtuple('Summary', 'category key value')

_FIELD_MEANING = dict(g='gauge', c='counter', ms='timer', s='set')

def getStatsdSamples(packet):
    """Get all samples in the packet

    :params packet: a statsd protocol packet
    :returns: iterable of Sample
    """
    for line in packet.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split(':')
        key = _cleanKey(parts.pop(0))
        for sample in parts:
            yield _parseSample(key, sample)

_ALLOWED_CHARACTERS = set(string.ascii_letters + string.digits + '_.-')

def _getBadCharacters():
    for i in range(256):
        if chr(i) not in _ALLOWED_CHARACTERS:
            yield chr(i)

_BAD_CHARACTERS = ''.join(_getBadCharacters())

def _cleanKey(key):
    key = '_'.join(key.split())
    key = key.replace('/', '.')
    key = key.translate(None, _BAD_CHARACTERS)
    return key

def _parseSample(key, sample):
    fields = sample.split('|')
    if len(fields) < 2:
        raise ValueError("Not enough fields", fields)
    if not fields[0]:
        fields[0] = '0'
    meaning = _FIELD_MEANING[fields.pop(1)]
    return Sample(meaning=meaning, key=key, fields=fields)

class Store(object):

    """Store of statistics"""

    def __init__(self, now):
        """Initialize

        :params now: Current time
        """
        self._reset(now)
        self.gauges = collections.defaultdict(int)

    def _reset(self, now):
        self.lastNow = now
        self.counters = collections.defaultdict(int)
        self.sets = collections.defaultdict(set)
        self.timers = collections.defaultdict(list)

    def getAndReset(self, now):
        """Get all aggregate statistics and reset them

        :params now: Current time
        :returns: Iterable of Summary
        """
        delta = now - self.lastNow
        for key, value in self.counters.iteritems():
            yield Summary(category='counters', key=key + '.count', value=value)
            yield Summary(category='counters', key=key + '.rate', value=value / delta)
        for key, value in self.gauges.iteritems():
            yield Summary(category='gauges', key=key, value=value)
        for key, value in self.sets.iteritems():
            yield Summary(category='sets', key=key + '.count', value=len(value))
        for key, value in self.timers.iteritems():
            summaries = _getTimerSummaries(value)
            for tp, summary in summaries.iteritems():
                yield Summary(category='timers', key=key + "." + tp, value=summary)
            yield Summary(category='timers',
                          key=key + ".count_ps",
                          value=summaries['count'] / delta)
        self._reset(now)

    def update(self, sample):
        """Update store with a sample

        :params sample: a Sample
        """
        getattr(self, '_update_'+sample.meaning)(sample)

    def _update_counter(self, sample):
        rateStr = (sample.fields[1:] or ['@1'])[0]
        rate = 1
        if rateStr.startswith('@'):
            rate = float(rateStr[1:])
        self.counters[sample.key] += float(sample.fields[0])/rate

    def _update_gauge(self, sample):
        val = sample.fields[0]
        if not val.startswith(('+', '-')):
            self.gauges[sample.key] = 0
        self.gauges[sample.key] += float(val)

    def _update_set(self, sample):
        self.sets[sample.key].add(sample.fields[0])

    def _update_timer(self, sample):
        value = float(sample.fields[0])
        self.timers[sample.key].append(value)

def _getTimerSummaries(numbers):
    ret = {}
    ret['count'] = len(numbers)
    numbers.sort()
    ret['lower'], ret['upper'] = numbers[0], numbers[-1]
    if len(numbers) < 2:
        numbers.append(numbers[0])
    p90idx = int(math.floor(.9*len(numbers)))
    del numbers[p90idx:]
    ret['upper_90'] = numbers[-1]
    ret['mean'] = sum(numbers) / len(numbers)
    return ret

## pylint: disable=too-few-public-methods

class UDPProtocol(tiprotocol.DatagramProtocol):

    """Implement a UDP protocol"""

    def __init__(self, update, parse):
        """Initialize

        :params update: A callable that takes an update object
        :params parse: A callable taking packet data and returning an
                       iterable of update objects
        """
        self.update = update
        self.parse = parse

    def datagramReceived(self, data, dummyPeer):
        """datagram received

        :params data: datagram data
        :params dummyPeer: (ignored) peer metadata
        """
        for summary in self.parse(data):
            self.update(summary)

## pylint: enable=too-few-public-methods

Metrics = collections.namedtuple('Metrics', 'metric value timestamp')

def publish(prefix, getSummaries, sender, timer):
    """Publish all metrics

    :params prefix: prefix for metric names
    :params getSummaries: callable that returns Summary iterable
                          and takes "current time"
    :params sender: callable that takes metrics and sends them to a metric
                    store
    :params timer: callable that returns current time
    """
    now = timer()
    for summary in getSummaries(now):
        name = '%s.%s.%s' % (prefix, summary.category, summary.key)
        sender(Metrics(metric=name, value=summary.value, timestamp=now))

class CarbonTextProtocol(tiprotocol.Protocol):

    """Carbon client protocol"""

    def __init__(self):
        self.factory = None

    def connectionMade(self):
        """Let the factory know the connection has been made"""
        self.factory.clientConnectionMade(self)

    def sendMetrics(self, metrics):
        """Send metrics to the server"""
        for metric in metrics:
            self.transport.write('%s %s %s\n' % (metric.metric, metric.value, metric.timestamp))

class MetricsSendingFactory(tiprotocol.ReconnectingClientFactory):

    """Factory that queues metrics and sends them to the server when connected"""

    def __init__(self, protocol):
        """Initialize

        :params protocol: A Protocol subclass
        """
        self.protocol = protocol
        self.proto = None
        self.metricsQueue = []

    def sendMetrics(self, metrics):
        """Send or queue metrics to be sent

        :params metrics: Iterable of Metric
        """
        if self.proto is None:
            self.metricsQueue.extend(metrics)
        else:
            self.proto.sendMetrics(metrics)

    def clientConnectionMade(self, proto):
        """Client connection succeeded

        Send all queued metrics

        :params proto: An instance of the protocol class
        """
        self.proto = proto
        self.proto.sendMetrics(self.metricsQueue)
        self.metricsQueue = []

    def clientConnectionLost(self, connector, reason):
        """Client connection terminated
        """
        tiprotocol.ReconnectingClientFactory.clientConnectionLost(self,
                                                                  connector,
                                                                  reason)
        self.proto = None

    def clientConnectionFailed(self, connector, reason):
        """Client connection failed
        """
        tiprotocol.ReconnectingClientFactory.clientConnectionFailed(self,
                                                                    connector,
                                                                    reason)
        self.proto = None

## pylint: disable=no-member
TCPClient, UDPServer = tainternet.TCPClient, tainternet.UDPServer
## pylint: enable=no-member

def makeService(opt):
    """Create statsd Application service

    :params opt: dict-like object with 'interface', 'port',
                 'carbon-host', 'carbon-port' and 'freq' keys
    """
    ret = service.MultiService()
    now = time.time()
    store = Store(now)
    dpProtocol = UDPProtocol(parse=getStatsdSamples, update=store.update)
    dpService = UDPServer(protocol=dpProtocol,
                          interface=opt['interface'],
                          port=opt['port'])
    dpService.setName('statsd')
    dpService.setServiceParent(ret)
    factory = MetricsSendingFactory(CarbonTextProtocol)
    clientService = TCPClient(factory=factory,
                              host=opt['carbon-host'],
                              port=opt['carbon-port'])
    clientService.setName('carbon')
    clientService.setServiceParent(ret)
    prefix = opt['prefix']
    publisher = tainternet.TimerService(opt['freq'],
                                        publish,
                                        prefix,
                                        store.getAndReset,
                                        factory.sendMetrics,
                                        time.time)
    publisher.setName('publisher')
    publisher.setServiceParent(ret)
    heart.maybeAddHeart(ret)
    return ret

## pylint: disable=too-few-public-methods

class Options(usage.Options):

    """Options for twistd ncolony-statsd plugin"""

    optParameters = [['prefix', None, None, "Prefix of all stats sent"],
                     ['carbon-host', None, None, "Address of Carbon server"],
                     ['carbon-port', None, 2003, "Port of Carbon server", int],
                     ['interface', None, '127.0.0.1', "Interface to listen on"],
                     ['port', None, 8125, "Port to listen on", int],
                     ['frequency', None, 60, "Frequency to send statistics", int],
                    ]

    def postOptions(self):
        """Checks that required carbon-host/prefix are present"""
        for param in ('carbon-host', 'prefix'):
            if self[param] is None:
                raise usage.UsageError("Missing required", param)

## pylint: enable=too-few-public-methods
