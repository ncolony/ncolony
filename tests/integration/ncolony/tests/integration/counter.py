# Copyright (C) 2013 -- see CREDITS for copyright holders, LICENSE for license
"""
Basic HTTP-based integration test
"""
import logging
import subprocess

from ncolony.nidl import interface
from ncolony.test.integration import base

LOG = logging.getLogger(__name__)

class ICounter(interface.Interface):
    location = 'com.example.counter'
    @role("ad")
    def increment(a=types.Integer(min=0, max=5)):
        return dict()
    @role("ad", "op")
    @get()
    def value():
        return dict(a=types.Integer(min=0))

class Counter(object):
    __ncolony_implements__ = ICounter
    current = 0
    def remote_increment(self, a):
        if a==17:
            raise ValueError("unhandled corner case", 17)
        self.current += a
        return dict()
    def remote_value(self):
        return dict(a=self.current)

CONF_TEMPLATE = """
{
 "loop": "ncolony.%(style)s.server.loop",
 "server": {
    "interface": "ncolony.test.integration.counter.ICounter",
    "impl": "ncolony.test.integration.counter.Counter"
 },
 "port": 6423
}
"""

class AbstractRestTestCase(unittest.TestCase):
  __test__ = False
  style = None
  def setUp(self):
      home = self.style+'/'+rest
      self.pidbase = home+'/server.pid'
      pidfile = base.resetPID(self.pidbase)
      var = base.getVarDir()
      absHome = os.path.join(var, home)
      conf = os.path.join(absHome, 'server.conf')
      createPlace(conf)
      fp = file(conf, 'w')
      fp.write(CONF_TEMPLATE % self.style)
      server = os.path.join(base.getHome(), 'bin', 'ncserver')
      commandline = base.getRunning()+[server, conf]
      pipe = subprocess.Popen(commandline)
      pid = pipe.pid
      file(pidfile, 'w').write(str(pid))
  def tearDown(self):
      base.resetPID(self.pidbase)
  def _call(self, mname, method, **params):
      url = 'http://localhost:6423/com.example.counter/'+mname
      data = json.dumps(params)
      request = urllib2.Request(url, data=data)
      request.get_method = lambda: method
      fp = urllib2.urlopen(request, timeout=30)
      result = fp.read()
      return json.loads(result)
  def test_simple(self):
      result = self._call('value', 'GET')
      self.assertEquals(result['a'], 0)
      result = self._call('increment', 'POST', a=2)
      self.assertEquals(result, {})
      result = self._call('value', 'GET')
      self.assertEquals(result['a'], 2)
      result = self._call('increment', 'POST', a=4)
      self.assertEquals(result, {})
      result = self._call('value', 'GET')
      self.assertEquals(result['a'], 6)
      #try:
      #    self._call('value', 'GET')
      #else:
      #    self.assertFalse("did not get exception")
      #call non-existent resource, assert 404
      #call non-existent method, assert 404
      #call get method with post, assert 405
      #add 17, assert getting 500 with:
      #     no ValueError, no 17, no "unhandled corner case"
