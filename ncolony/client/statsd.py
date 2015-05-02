_formatters = {}

def _isFormatter(func):
    formatters[func.__name__.lstrip('_')] = func

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
    data = formatters[tp](value)
    return '{}:{}'.format(stat, data)

## Characteristic
class _Pipeline(object):

    def __init__(self, original, maxsize, delay, reactor, preprocess):
        self.original = original
        self.maxsize = maxsize
        self.reactor = reactor
        self.preprocess = preprocess
        self.delay = delay
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

class _ConnectingUDPProtocol(protocol.DatagramProtocol):

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

def makePipeline(maxsize=512, delay=1, host='127.0.0.1', port=8125, interface='127.0.0.1', reactor=None, prefix=''):
    if reactor == None:
        from twisted.internet import reactor as defaultReactor
        reactor = defaultReactor
    original = _ConnectingUDPProtocol(host, port)
    pipeline = _Pipeline(original, maxsize, delay, reactor, _preprocess)
    @functools.wraps(_format)
    def _send(*args, **kwargs):
        rate = kwargs.get('rate')
        if rate != None and rate != 1 and random.random()<rate:
            return
        if kwargs.get('prefix') == None:
            kwargs['prefix'] = prefix
        formatted = _format(*args, **kwargs)
        pipeline.write(formatted)
    reactor.listenUDP(0, original)
    return _send

_SENDERS = []

def addClient(sender):
    _SENDERS.append(sender)

def clearClients():
    _SENDERS[:] = []

def sendStat(stat, tp, value, prefix=None, rate=None):
    for sender in _SENDER:
        sender(stat=stat, tp=tp, value=value, prefix=prefix, rate=rate)
