# Copyright (c) Moshe Zadka
# See LICENSE for details.

"""Example of deployment"""

if __name__ != '__main__':
    raise ImportError("This module is not designed to be imported", __name__)

import os
import sys

from twisted.python import filepath

from ncolony import ctllib

binLocation = os.path.join(os.environ['VIRTUAL_ENV'], 'bin')
root = os.path.dirname(os.path.dirname(os.path.abspath(__import__(__package__).__file__)))

tempDir = os.path.join(root, 'build', '_example')

root = filepath.FilePath(tempDir)
if root.child('twistd.pid').exists():
    sys.exit("Running twistd, aborting")
if root.exists():
    root.remove()
root.makedirs()

tac = root.child('example.tac')
tac.setContent("""
import time

from zope import interface as zinterface
from twisted.internet import reactor, endpoints
from twisted.web import resource, static, server
from twisted.application import internet, service

from ncolony.client import heart

begin = resource.Resource()
hello = static.Data(type='text/html', data='Hello world')
begin.putChild('', hello)

class Die(object):
    zinterface.implements(resource.IResource)
    isLeaf = True
    def render(self, request):
        reactor.stop()

class Spin(object):
    zinterface.implements(resource.IResource)
    isLeaf = True
    def render(self, request):
        while True:
            time.sleep(1000)

begin.putChild('die', Die())
begin.putChild('spin', Spin())
site = server.Site(begin)
port = endpoints.TCP4ServerEndpoint(reactor, 8000, interface='127.0.0.1')
webService = internet.StreamServerEndpointService(endpoint=port, factory=site)
application = service.Application("bad-web-server")
webService.setServiceParent(application)
heart.maybeAddHeart(application)
""")

config = root.child('config')
messages = root.child('messages')
status = root.child('status')
for subd in (config, messages, status):
    subd.createDirectory()

places = ctllib.Places(config=config.path, messages=messages.path)
extras = {'ncolony.beatcheck': dict(status=status.child('example').path, period=1, grace=1)}
twistd = os.path.join(binLocation, 'twistd')
ctllib.add(places, name='example', cmd=twistd,
           args=['--logfile', root.child('example.log').path, '-ny', tac.path], extras=extras)
ctllib.add(places, name='beatcheck', cmd=twistd,
           args=['--logfile', root.child('beatcheck.log').path,
                 '-n', 'ncolony-beatcheck',
                 '--messages='+places.messages,
                 '--config='+places.config])
args = (twistd,
        '--logfile='+root.child('master.log').path,
        '--pidfile='+root.child('twistd.pid').path,
        'ncolony',
        '--messages='+places.messages, '--config='+places.config, '--freq', '1')
os.execv(args[0], args)
