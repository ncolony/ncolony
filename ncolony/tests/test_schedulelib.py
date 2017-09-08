# Copyright (c) Moshe Zadka
# See LICENSE for details.

"""Test ncolony.schedulelib"""

from __future__ import division

import os
import unittest
import sys

import six

from zope.interface import verify

from twisted.python import failure

from twisted.internet import defer
from twisted.internet import interfaces as tiinterfaces
from twisted.internet import reactor

from twisted.application import internet as tainternet

from twisted.runner.test import test_procmon

from ncolony import schedulelib

from ncolony.client.tests import test_heart

class TestProcessProtocol(unittest.TestCase):

    """Test schedulelib.ProcessProtocol"""

    def setUp(self):
        out = six.StringIO()
        oldstdout = sys.stdout
        def _cleanup():
            sys.stdout = oldstdout
        self.addCleanup(_cleanup)
        sys.stdout = out
        self.deferred = defer.Deferred()
        self.pp = schedulelib.ProcessProtocol(self.deferred)

    def test_process_stdout_one_line(self):
        """Test one stdout line"""
        self.pp.childDataReceived(1, "hello")
        self.assertEquals(sys.stdout.getvalue(), '[1] hello\n')

    def test_process_stdout_two_line(self):
        """Test two stdout lines"""
        self.pp.childDataReceived(1, "hello\nworld")
        self.assertEquals(sys.stdout.getvalue(), '[1] hello\n[1] world\n')

    def test_process_stderr_one_line(self):
        """Test one stderr line"""
        self.pp.childDataReceived(2, "hello")
        self.assertEquals(sys.stdout.getvalue(), '[2] hello\n')

    def test_end(self):
        """Test process end"""
        myfail = failure.Failure(ValueError("nonono"))
        self.pp.processEnded(myfail)
        result = []
        self.deferred.addErrback(result.append)
        self.assertIs(result[0], myfail)

    def test_implements(self):
        """Test object implements the right interface"""
        self.assertTrue(verify.verifyObject(tiinterfaces.IProcessProtocol, self.pp))

    def test_doesnt_break(self):
        """Test required methods do not fail"""
        self.pp.processExited(None)
        self.pp.childConnectionLost(None)
        self.pp.makeConnection(None)

class TestRunProcess(unittest.TestCase):

    """Test schedulelib.runProcess"""

    def setUp(self):
        self.reactor = test_procmon.DummyProcessReactor()
        out = six.StringIO()
        oldstdout = sys.stdout
        def _cleanup():
            sys.stdout = oldstdout
        self.addCleanup(_cleanup)
        sys.stdout = out

    def test_run_process_simple(self):
        """Test process successful termination causes a log message"""
        args = ['/bin/echo', 'hello']
        timeout = 10
        grace = 2.5
        results = []
        deferred = schedulelib.runProcess(args, timeout, grace, self.reactor)
        deferred.addCallback(results.append)
        process, = self.reactor.spawnedProcesses
        self.assertIsInstance(process.proto, schedulelib.ProcessProtocol)
        ## pylint: disable=protected-access
        self.assertIs(process._reactor, self.reactor)
        self.assertIs(process._executable, args[0])
        self.assertIs(process._args, args)
        self.assertIs(process._environment, os.environ)
        ## pylint: enable=protected-access
        terminate, kill = self.reactor.getDelayedCalls()
        self.assertTrue(terminate.active())
        self.assertEquals(terminate.getTime(), timeout)
        self.assertTrue(kill.active())
        self.assertEquals(kill.getTime(), timeout+grace)
        process.processEnded(0)
        self.assertFalse(terminate.active())
        self.assertFalse(kill.active())
        dummy, = results
        output = sys.stdout.getvalue()
        message = ('A process has ended without apparent errors: '
                   'process finished with exit code 0.\n')
        self.assertEquals(output, message)

    def test_run_process_failing(self):
        """Test process failure causes a log message"""
        args = ['/bin/echo', 'hello']
        timeout = 10
        grace = 2.5
        results = []
        deferred = schedulelib.runProcess(args, timeout, grace, self.reactor)
        deferred.addCallback(results.append)
        process, = self.reactor.spawnedProcesses
        terminate, kill = self.reactor.getDelayedCalls()
        process.processEnded(1)
        self.assertFalse(terminate.active())
        self.assertFalse(kill.active())
        dummy, = results
        output = sys.stdout.getvalue()
        message = ('A process has ended with a probable error condition: '
                   'process ended with exit code 1.\n')
        self.assertEquals(output, message)

    def test_run_process_stuck(self):
        """Test process gets TERM if it does not end by itself"""
        args = ['/bin/echo', 'hello']
        timeout = 10
        grace = 2.5
        results = []
        deferred = schedulelib.runProcess(args, timeout, grace, self.reactor)
        deferred.addCallback(results.append)
        dummy, = self.reactor.spawnedProcesses
        terminate, kill = self.reactor.getDelayedCalls()
        self.reactor.advance(10)
        self.assertFalse(terminate.active())
        self.assertTrue(kill.active())
        self.reactor.advance(2)
        self.assertFalse(kill.active())
        dummy, = results
        output = sys.stdout.getvalue()
        message = ('A process has ended without apparent errors: '
                   'process finished with exit code 0.\n')
        self.assertEquals(output, message)

    def test_run_process_stuck_hard(self):
        """Test process gets KILL if TERM doesn't kill it"""
        args = ['/bin/echo', 'hello']
        timeout = 10
        grace = 0.5
        results = []
        deferred = schedulelib.runProcess(args, timeout, grace, self.reactor)
        deferred.addCallback(results.append)
        dummy, = self.reactor.spawnedProcesses
        terminate, kill = self.reactor.getDelayedCalls()
        self.reactor.advance(10)
        self.assertFalse(terminate.active())
        self.assertTrue(kill.active())
        self.reactor.advance(0.7)
        self.assertFalse(kill.active())
        dummy, = results
        output = sys.stdout.getvalue()
        message = ('A process has ended with a probable error condition: '
                   'process ended with exit code 1.\n')
        self.assertEquals(output, message)

    def test_run_process_pass_through_unexpected_fail(self):
        """Test that non-process-related failures fall through"""
        args = ['/bin/echo', 'hello']
        timeout = 10
        grace = 2.5
        results = []
        deferred = schedulelib.runProcess(args, timeout, grace, self.reactor)
        deferred.addErrback(results.append)
        deferred.errback(failure.Failure(ValueError("HAHA")))
        dummy, = results

class TestService(unittest.TestCase):

    """Test the service"""

    def setUp(self):
        self.parser = schedulelib.Options()
        self.args = dict(arg='/bin/echo hello',
                         timeout='10',
                         grace='2',
                         frequency='30',
                        )

    def getArgs(self):
        """Get the arguments as a list of strings"""
        return ' '.join(' '.join('--%s %s' % (key, vpart) for vpart in value.split())
                        for key, value in six.iteritems(self.args)).split()

    def test_normal(self):
        """Test correct parsing of a command line"""
        args = self.getArgs()
        self.parser.parseOptions(args)
        self.assertEquals(self.parser['args'], ['/bin/echo', 'hello'])
        self.assertEquals(self.parser['timeout'], 10)
        self.assertEquals(self.parser['grace'], 2)
        self.assertEquals(self.parser['frequency'], 30)

    def helper_test_required(self, value):
        """Helper method: test that a given parameter is required"""
        del self.args[value]
        with self.assertRaises(ValueError):
            self.parser.parseOptions(self.getArgs())

    def test_required_args(self):
        """Test that at least one argument is required"""
        self.helper_test_required('arg')

    def test_required_timeout(self):
        """Test that timeout is required"""
        self.helper_test_required('timeout')

    def test_required_grace(self):
        """Test that grace is required"""
        self.helper_test_required('grace')

    def test_required_frequency(self):
        """Test that frequency is required"""
        self.helper_test_required('frequency')

    def test_make_service(self):
        """Test the make service function"""
        opts = {}
        opts['args'] = ['/bin/echo', 'hello']
        opts['timeout'] = 10
        opts['grace'] = 2
        opts['frequency'] = 30
        masterService = schedulelib.makeService(opts)
        service = masterService.getServiceNamed('scheduler')
        self.assertIsInstance(service, tainternet.TimerService)
        func, args, kwargs = service.call
        self.assertFalse(kwargs)
        self.assertIs(func, schedulelib.runProcess)
        self.assertEquals(args, (opts['args'], opts['timeout'], opts['grace'], reactor))
        self.assertEquals(service.step, opts['frequency'])

    def test_make_service_with_health(self):
        """Test schedulelib with heart beater"""
        opts = dict(timeout=10, grace=2, frequency=30)
        opts['args'] = ['/bin/echo', 'hello']
        myEnv = test_heart.buildEnv()
        test_heart.replaceEnvironment(self, myEnv)
        masterService = schedulelib.makeService(opts)
        service = masterService.getServiceNamed('heart')
        test_heart.checkHeartService(self, service)
