import characteristic

from zope import interface

from twisted.internet import protocol
from twisted.application import service

_formatters = {}

def _isFormatter(func):
    _formatters[func.__name__.lstrip('_')] = func

@_isFormatter
def _timing(delta):
    return '{:d}|ms'.format(delta)

@_isFormatter
def _incr(delta):
    return '{:d}|c'.format(delta)

@_isFormatter
def _decr(delta):
    return incr(stat, -delta)

@_isFormatter
def _set(value):
    return '{}|c'.format(value)

@_isFormatter
def _gaugeDelta(value):
    if value > 0:
        prefix = '+'
    else:
        prefix = ''

## TODO - Gauge set

def _format(stat, tp, value, prefix):
    if prefix != '':
        prefix += '.'
    stat = prefix + stat
    data = _formatters[tp](value)
    return '{}:{}'.format(stat, data)

@characteristic.immutable([characteristic.Attribute('original'),
                           characteristic.Attribute('maxsize'),
                           characteristic.Attribute('delay'),
                           characteristic.Attribute('reactor'),
                           characteristic.Attribute('preprocess'),
                          ])
class _Pipeline(object):

    def __init__(self):
        self.outstanding = None
        self.buffer = ''

    def _reallyWrite(self):
        if self.outstanding:
            if not self.outstanding.called:
                self.outstanding.cancel()
            self.outstanding = None
        self.original.write(preprocess(self.buffer))
        self.buffer = ''

    def write(self, datum):
        if len(self.buffer) + len(datum) > 0:
            self._reallySend()
            return
        self.buffer += datum
        if self.outstanding:
            return
        self.outstanding = reactor.callLater(delay, self._reallyWrite)

@characteristic.immutable([characteristic.Attribute('host'),
                           characteristic.Attribute('port')])
class _ConnectingUDPProtocol(object, protocol.DatagramProtocol):

    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.transport = None

    def startProtocol(self):
        self.transport.connect(self.host, self.port)

    def write(self, data):
        if self.transport is None:
            return
        self.transport.write(data)

def _preprocess(s):
    return s.rstrip('\n')

@characteristic.immutable([characteristic.Attribute('maxsize', default_value=512),
                           characteristic.Attribute('delay', default_value=1),
                           characteristic.Attribute('host', default_value='127.0.0.1'),
                           characteristic.Attribute('port', default_value=8125),
                           characteristic.Attribute('interface', default_value='127.0.0.1'),
                           characteristic.Attribute('reactor', None),
                           characteristic.Attribute('prefix', ''),
                          ])
class Params(object):
    pass

@characteristic.immutable([characteristic.Attribute('sender'),
                           characteristic.Attribute('protocol')])
class Client(object):
    pass

def makeClient(params):
    reactor = params.reactor
    if params.reactor == None:
        from twisted.internet import reactor as defaultReactor
        reactor = defaultReactor
    original = _ConnectingUDPProtocol(params.host, params.port)
    pipeline = _Pipeline(original, params.maxsize, params.delay, reactor, _preprocess)
    formatter = functools.partial(format, prefix=params.prefix)
    sender = functools.partial(_sendToPipeline, pipeline=pipeline, randomizer=random.random, formatter=formatter)
    return Client(sender=sender, protocol=original)

_SENDERS = []

def addClient(sender):
    _SENDERS.append(sender)

def removeClient(sender):
    _SENDERS.remove(sender)

def _sendToPipeline(pipeline, randomizer, formatter, stat, tp, value, prefix=None, rate=None):
    if rate != None and rate != 1 and randomizer() < rate:
        return
    if prefix == None:
        prefix = defaultPrefix
    formatted = _format(*args, **kwargs)
    pipeline.write(formatted)

def sendStat(stat, tp, value, prefix=None, rate=None):
    for sender in _SENDERS:
        sender(stat=stat, tp=tp, value=value, prefix=prefix, rate=rate)

class Service(object):

    interface.implements(service.IService)

    def __init__(self, client):
        self.client = client

    def privilegedStartService(self):
        pass

    def startService(self):
        addClient(self.client.sender)
        self.port = reactor.listenUDP(0, self.client.original)

    def stopService(self):
        removeClient(self.client.sender)
        self.port.stopListening()

    @classmethod
    def fromDetails(cls, **kwargs):
        params = Params(**kwargs)
        client = makeClient(params)
        return cls(client)
