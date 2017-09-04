# Copyright (c) Moshe Zadka
# See LICENSE for details.

"""ncolony.tests.test_service -- test Twisted service"""

import collections
import json
import os
import shutil
import unittest

from zope.interface import verify

from twisted.python import usage
from twisted.internet import reactor
from twisted.application import service as taservice, internet
from twisted.runner import procmon
from twisted.runner.test import test_procmon

from ncolony import service

class DummyFile(object):

    """filepath.FilePath clone"""

    def __init__(self, name):
        self.name = name
        self.content = None
        self.removed = False
        self.children = {}

    def child(self, childName):
        """Return a fake child"""
        if childName in self.children:
            return self.children[childName]
        ret = DummyFile(self.name + "/" + childName)
        self.children[childName] = ret
        return ret

    def setContent(self, content):
        """Set file contents"""
        self.content = content

    def remove(self):
        """Remove file"""
        self.removed = True

DummyTransport = collections.namedtuple('DummyTransport', 'pid')

class TestTransportDirectoryDict(unittest.TestCase):

    """Test TransportDirectoryDict"""

    def setUp(self):
        self.file = DummyFile('')
        self.tdd = service.TransportDirectoryDict(self.file)

    def test_add_remove(self):
        """Test adding a file and then removing it"""
        self.tdd['foo'] = DummyTransport(100)
        self.assertEquals(self.tdd['foo'], DummyTransport(100))
        thing = self.file.children['foo']
        self.assertEquals(thing.content, '100')
        self.assertEquals(thing.removed, False)
        del self.tdd['foo']
        self.assertNotIn('foo', self.tdd)
        self.assertEquals(thing.removed, True)

## pylint: disable=protected-access

class TestService(unittest.TestCase):

    """Test the service"""

    def setUp(self):
        """Set up the test"""
        def _cleanup(testDir):
            if os.path.exists(testDir):
                shutil.rmtree(testDir)
        self.testDirs = {}
        for subd in ['config', 'messages']:
            testDir = self.testDirs[subd] = os.path.join(os.getcwd(), subd)
            self.addCleanup(_cleanup, testDir)
            _cleanup(testDir)
            os.makedirs(testDir)
        self.my_reactor = test_procmon.DummyProcessReactor()
        self.service = service.get(self.testDirs['config'], self.testDirs['messages'],
                                   5, reactor=self.my_reactor)
        self._finishSetUp()

    def _finishSetUp(self):
        subservices = list(self.service)
        self.pm = self.service.getServiceNamed('procmon')
        subservices.remove(self.pm)
        self.subservices = subservices
        self.functions = [s.call[0] for s in self.subservices]
        self.pm.startService()

    def test_with_piddir(self):
        """Test service with piddir"""
        pidDir = DummyFile('')
        self.service = service.get(self.testDirs['config'], self.testDirs['messages'],
                                   5, pidDir=pidDir, reactor=self.my_reactor)
        self._finishSetUp()
        protocols = self.pm.protocols
        self.assertIsInstance(protocols, service.TransportDirectoryDict)
        self.assertIs(protocols.output, pidDir)

    def test_regular_reactor(self):
        """Test that the default reactor is the default reactor"""
        myserv = service.get('', '', 5)
        pm = myserv.getServiceNamed('procmon')
        self.assertEquals(pm._reactor, reactor)

    def _check(self):
        for f in self.functions:
            f()

    def _write(self, tp, name, content):
        name = os.path.join(self.testDirs[tp], name)
        with open(name, 'w') as fp:
            fp.write(content)

    def _remove(self, tp, name):
        name = os.path.join(self.testDirs[tp], name)
        os.remove(name)

    def test_iface(self):
        """Test that the service has the right interface"""
        iface = taservice.IServiceCollection
        verify.verifyObject(iface, self.service)

    def test_subservices(self):
        """Test that the service has the right subservices"""
        self.assertIsInstance(self.pm, procmon.ProcessMonitor)
        self.assertIs(self.pm._reactor, self.my_reactor)
        self.assertEquals(len(self.subservices), 2)
        for subservice in self.subservices:
            self.assertIsInstance(subservice, internet.TimerService)
            self.assertEquals(subservice.step, 5)
            _, args, kwargs = subservice.call
            self.assertFalse(args)
            self.assertFalse(kwargs)

    def test_one_add(self):
        """Test that the service can add one process"""
        content = json.dumps(dict(args=['/bin/echo', 'hello']))
        self._write('config', 'one', content)
        self._check()
        process, = self.my_reactor.spawnedProcesses
        self.assertEquals(process._args, ['/bin/echo', 'hello'])

    def test_add_and_restart(self):
        """Test that the service can restart a process"""
        content = json.dumps(dict(args=['/bin/echo', 'hello']))
        self._write('config', 'one', content)
        self._check()
        restart = json.dumps(dict(type='RESTART', name='one'))
        self._write('messages', '00Message', restart)
        self._check()
        self.my_reactor.advance(60)
        process, _ = self.my_reactor.spawnedProcesses
        self.assertFalse(process.pid)

class TestOptions(unittest.TestCase):

    """Test option parsing"""

    def setUp(self):
        """Set up the test"""
        self.opt = service.Options()
        self.basic = ['--message', 'message-dir', '--config', 'config-dir']

    def test_commandLineRequired(self):
        """Test failure on missing command line"""
        with self.assertRaises(usage.UsageError):
            self.opt.parseOptions([])

    def test_basic(self):
        """Test basic command line parsing"""
        self.opt.parseOptions(self.basic)
        self.assertEqual(self.opt['messages'], 'message-dir')
        self.assertEqual(self.opt['config'], 'config-dir')
        self.assertEqual(self.opt['threshold'], 1)
        self.assertEqual(self.opt['killtime'], 5)
        self.assertEqual(self.opt['minrestartdelay'], 1)
        self.assertEqual(self.opt['maxrestartdelay'], 3600)
        self.assertEqual(self.opt['frequency'], 10)
        self.assertEqual(self.opt['pid'], None)

    def test_pid(self):
        """Test explicit pid"""
        self.opt.parseOptions(self.basic+['--pid', 'pid-dir'])
        self.assertEqual(self.opt['pid'], 'pid-dir')

    def test_threshold(self):
        """Test explicit threshold"""
        self.opt.parseOptions(self.basic+['--threshold', '7.5'])
        self.assertEqual(self.opt['threshold'], 7.5)

    def test_killTime(self):
        """Test explicit killtime"""
        self.opt.parseOptions(self.basic+['--killtime', '7.5'])
        self.assertEqual(self.opt['killtime'], 7.5)

    def test_minRestartDelay(self):
        """Test explicit min restart delay"""
        self.opt.parseOptions(self.basic+['--minrestartdelay', '7.5'])
        self.assertEqual(self.opt['minrestartdelay'], 7.5)

    def test_maxRestartDelay(self):
        """Test explicit max restart delay"""
        self.opt.parseOptions(self.basic+['--maxrestartdelay', '7.5'])
        self.assertEqual(self.opt['maxrestartdelay'], 7.5)

    def test_frequency(self):
        """Test explicit frequency"""
        self.opt.parseOptions(self.basic+['--maxrestartdelay', '7.5'])
        self.opt.parseOptions(self.basic+['--frequency', '7.5'])
        self.assertEqual(self.opt['frequency'], 7.5)

    def test_makeservice(self):
        """Test makeService"""
        self.opt.parseOptions(self.basic+
                              ['--threshold', '0.5']+
                              ['--killtime', '1.5']+
                              ['--minrestartdelay', '2.5']+
                              ['--maxrestartdelay', '3.5']+
                              ['--frequency', '4.5']+
                              ['--pid', 'pid-dir'])
        s = service.makeService(self.opt)
        pm = s.getServiceNamed('procmon')
        self.assertIsInstance(pm, procmon.ProcessMonitor)
        subservices = list(s)
        subservices.remove(pm)
        functions = [subs.call[0] for subs in subservices]
        paths = set()
        for func in functions:
            paths.add(func.args[0].basename())
        self.assertEquals(paths, set(['message-dir', 'config-dir']))
        protocols = pm.protocols
        self.assertIsInstance(protocols, service.TransportDirectoryDict)
        self.assertIs(protocols.output, 'pid-dir')
        self.assertEquals(subservices[0].step, 4.5)
        self.assertEquals(pm.threshold, 0.5)
        self.assertEquals(pm.killTime, 1.5)
        self.assertEquals(pm.minRestartDelay, 2.5)
        self.assertEquals(pm.maxRestartDelay, 3.5)
