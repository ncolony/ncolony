## import characteristic
## 
## from zope import interface
## 
## from twisted.internet import protocol
## from twisted.application import service

_formatters = {}

def _isFormatter(func):
    _formatters[func.__name__.lstrip('_')] = func
    return func

def _format(stat, tp, value, prefix):
    if prefix != None:
        stat = prefix + '.' + stat
    data = _formatters[tp](value)
    data = '{}:{}'.format(stat, data)
    ## for line in data.splitlines():
    ##     return '{}:{}'.format(stat, line)
    return data

@_isFormatter
def _timing(delta):
    if delta == None:
        raise ValueError('timing without value')
    return '{:d}|ms'.format(delta)

@_isFormatter
def _incr(delta):
    if delta == None:
        delta = 1
    return '{:d}|c'.format(delta)

@_isFormatter
def _decr(delta):
    if delta == None:
        delta = 1
    return _incr(-delta)

@_isFormatter
def _set(value):
    if value == None:
        raise ValueError('set without value')
    return '{}|s'.format(value)

@_isFormatter
def _gaugeDelta(value):
    if value == None:
        raise ValueError('gaugeDelta without value')
    if value > 0:
        prefix = '+'
    else:
        prefix = ''
    return '{}{}|g'.format(prefix, value)

## @_isFormatter
## def _gaugeSet(value):
##     if value == None:
##         raise ValueError('gaugeSet without value')
##     if value < 0:
##         prefix = '0|g\n'
##     else:
##         prefix = ''
##     return '{}{}|g'.format(prefix, value)
## 
## ## TODO - Gauge set
## 

## @characteristic.immutable([characteristic.Attribute('original'),
##                            characteristic.Attribute('maxsize'),
##                            characteristic.Attribute('delay'),
##                            characteristic.Attribute('reactor'),
##                            characteristic.Attribute('preprocess'),
##                           ])
## class _Pipeline(object):
## 
##     def __init__(self):
##         self.outstanding = None
##         self.buffer = ''
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
## def sendStat(stat, tp, value=None, rate=None):
##     for sender in _SENDERS:
##         sender(stat=stat, tp=tp, value=value, rate=rate)
##
## class _StatsSender(object):
##
##     def __init__(self):
##        for formatter in _formatters:
##            setattr(self, formatter, _StatsSenderMetric(formatter))
##
## class _StatsSenderMetric(object):
##
##     def __init__(self, formatter, prefix=''):
##         self._prefix = prefix
##         self._formatter = formatter
## 
##     def __getattr__(self, name):
##         return StatsSenderMetric(self._formatter, self._prefix+'.'+name)
##
##     def __call__(self, value=None, rate=None):
##         sendStat(self._prefix, self._formatter, value=value, rate=None)
##
##
## metric = _StatsSender()
##
## class Service(object):
## 
##     interface.implements(service.IService)
## 
##     def __init__(self, client):
##         self.client = client
##         self.setServiceName('statsd')
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
##
##     @classmethod
##     def fromEnvironment(cls):
##         config = json.loads(os.environ['NCOLONY_CONFIG'])
##         kwargs = config.get('ncolony.client.statsd')
##         if kwargs != None:
##             return cls.fromDetails(cls, **kwargs)
##
##    @classmethod
##    def enhanceMultiService(cls, ms):
##        inst = cls.fromEnvironment()
##        if inst != None:
##            inst.setServiceParent(ms)
##
## Suggested usage:
## in makeService, add:
##     statsd.Service.enhanceMultiService(ms)
##
## in client code, add
## class Login(resource.Resource):
##     def render_GET(self, request):
##         statsd.metric.login.hits.incr()
## For example
