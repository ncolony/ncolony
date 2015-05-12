import characteristic
## 
## from zope import interface
## 
from twisted.internet import protocol
## from twisted.application import service

_formatters = {}

def _isFormatter(func):
    _formatters[func.__name__.lstrip('_')] = func
    return func

def _format(stat, tp, value, prefix):
    if prefix != None:
        stat = prefix + '.' + stat
    data = _formatters[tp](value)
    things = []
    for line in data.splitlines():
        things.append('{}:{}'.format(stat, line))
    return '\n'.join(things)

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

@_isFormatter
def _gaugeSet(value):
    if value == None:
        raise ValueError('gaugeSet without value')
    if value < 0:
        prefix = '0|g\n'
    else:
        prefix = ''
    return '{}{}|g'.format(prefix, value)

@characteristic.attributes([characteristic.Attribute('originalWrite'),
                           characteristic.Attribute('maxsize'),
                           characteristic.Attribute('delay'),
                           characteristic.Attribute('reactor'),
                          ],
                          apply_immutable=True)
class _Pipeline(object):

    def __init__(self):
        self.outstanding = None
        self.buffer = ''

    def _reallyWrite(self):
        if self.outstanding:
           if not self.outstanding.called:
               self.outstanding.cancel()
           self.outstanding = None
        self.originalWrite(self.buffer)
        self.buffer = ''

    def write(self, datum):
        if len(self.buffer) + len(datum) > self.maxsize:
            self._reallyWrite()
        self.buffer += datum
        if self.outstanding:
            return
        self.outstanding = self.reactor.callLater(self.delay, self._reallyWrite)

@characteristic.attributes([characteristic.Attribute('host'),
                            characteristic.Attribute('port'),
                           ],
                           apply_immutable=True)
class _ConnectingUDPProtocol(object, protocol.DatagramProtocol):

    def startProtocol(self):
        self.transport.connect(self.host, self.port)

## def write(protocol, buffer):
##    transport = protocol.transport
##     if transport == None:
##        return
##     buffer = buffer.rstrip('\n')
##     transport.write(buffer)
## 
## @characteristic.attributes([characteristic.Attribute('sender'),
##                             characteristic.Attribute('tp'),
##                             characteristic.Attribute('path'),
##                            ],
##                           apply_immutable=True)
## class _TypedMetricSender(object):
## 
##     def __getattr__(self, name):
##         if name.startswith('_'):
##             raise AttributeError(name)
##         return self.__class__(sender=self.sender, tp=self.tp, path=self.path+[name])
## 
##     def __call__(self, value=None, rate=None):
##         self.sender.send(self.tp, '.'.join(self.path), value, rate)
## 
## @characteristic.attributes([characteristic.Attribute('target'),
##                             characteristic.Attribute('prefix', default=''),
##                             characteristic.Attribute('rate', default=1),
##                             characteristic.Attribute('randomizer', default=random.random),
##                            ],
##                            apply_immutable=True)
## class MetricsSender(object):
## 
##     def __getattr__(self, name):
##         if name not in _formatters:
##             raise AttributeError(name)
##         return _TypedMetricsSender(tp=name, sender=self, path=[])
## 
##     def send(self, tp, stat, value=None, rate=None):
##         if rate == None:
##             rate = self.params.rate
##         if rate < 1 and rate < self.randomizer():
##             return
##         formatted = _format(stat, tp, value, self.params.prefix)
##         self.target(formatted + '\n')

## class DummySender(object):
## 
##     def __getattr__(self, name):
##         if name not in _formatters and name.startswith('_'):
##             raise AttributeError(name)
##         return self
## 
##     def __call__(self, value=None, rate=None):
##         pass
## 
##     def send(self, tp, stat, value=None, rate=None):
##         pass
## 
## _SENDER = DummySender()
## 
## def setSender(sender):
##     global _SENDER
##     _SENDER = sender
## 
## def unsetSender():
##     global _SENDER
##     _SENDER = DummySender()
## 
## def getSender():
##     return _SENDER

## @characteristic.attributes([characteristic.Attribute('metricsSender'),
##                             characteristic.Attribute('protocol'),
##                             characteristic.Attribute('interface'),
##                             characteristic.Attribute('reactor'),
##                            ],
##                            apply_immutable=True)
## class Service(object):
## 
##     interface.implements(service.IService)
## 
##     def __init__(self):
##         self.setServiceName('statsd')
## 
##     def privilegedStartService(self):
##         pass
## 
##     def startService(self):
##         setSender(self.metricsSender)
##         self.port = self.reactor.listenUDP(0, self.protocol)
## 
##     def stopService(self):
##         unsetSender(self.metricsSender)
##         self.port.stopListening()
## 
##     @classmethod
##     def fromParameters(cls, host='127.0.0.1', port=8125, interfce='127.0.0.1', prefix='', rate=1, maxsize=512, delay=0.5, reactor=None):
##         if reactor == None:
##             from twisted.internet import reactor as myReactor
##             reactor = myReactor 
##         protocol = _ConnectedUDPProtocol(host=host, port=port)
##         originalWrite = functools.partial(write, protocol)
##         pipeline = _Pipeline(originalWrite=originalWrite, maxsize=maxsize, delay=delay, reactor=reactor)
##         target = pipeline.write
##         sender = MetricsSender(target=target, prefix=prefix, rate=rate, randomizer=random.random)
##         return cls(metricsSender=sender, protocol=protocol, interface=interface, reactor=reactor)
## 
##     @classmethod
##     def fromEnvironment(cls):
##         config = json.loads(os.environ['NCOLONY_CONFIG'])
##         kwargs = config.get('ncolony.client.statsd')
##         if kwargs != None:
##             return cls.fromParameters(**kwargs)
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
##         statsd.getSender().login.hits.incr()
## For example
