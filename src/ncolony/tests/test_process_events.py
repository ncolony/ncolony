# Copyright (c) Moshe Zadka
# See LICENSE for details.
"""Test event processing"""
import unittest

from zope.interface import verify

from twisted.python import log

from ncolony import process_events
from ncolony import interfaces

from ncolony.tests import helper


class DummyProcessMonitor:

    """Something that looks like a process monitor"""

    def __init__(self):
        """Initialize to record which events we got"""
        self.events = []

    # pylint: disable=too-many-arguments
    def addProcess(self, name, args, uid=None, gid=None, env=None):
        """Add a process

        TODO: document arguments
        """
        if env is None:
            env = {}
        self.events.append(("ADD", name, args, uid, gid, env))

    # pylint: enable=too-many-arguments

    def removeProcess(self, name):
        """Remove a process

        TODO: document arguments
        """
        self.events.append(("REMOVE", name))

    def stopProcess(self, name):
        """Stop (really, restart) a process.

        TODO: document arguments
        """
        self.events.append(("RESTART", name))

    def restartAll(self):
        """Restart all processes"""
        self.events.append(("RESTART-ALL",))


class TestReceiver(unittest.TestCase):

    """Test the event receiver"""

    def setUp(self):
        """Initialize the test"""
        self.monitor = DummyProcessMonitor()
        self.receiver = process_events.Receiver(self.monitor)
        self.assertFalse(self.monitor.events)
        self.logMessages = []

        def _observer(msg):
            self.logMessages.append("".join(msg["message"]))

        self.addCleanup(log.removeObserver, _observer)
        log.addObserver(_observer)
        self.assertFalse(self.logMessages)

    def test_recorder_is_good(self):
        """Test that the recorder implements the right interface"""
        self.assertTrue(
            verify.verifyObject(interfaces.IMonitorEventReceiver, self.receiver)
        )

    def test_add_simple(self):
        """Test a simple process addition"""
        message = helper.dumps2utf8(dict(args=["/bin/echo", "hello"]))
        self.receiver.add("hello", message)
        self.assertEqual(len(self.monitor.events), 1)
        ((tp, name, args, uid, gid, env),) = self.monitor.events
        self.assertEqual(tp, "ADD")
        self.assertEqual(name, "hello")
        self.assertEqual(args, ["/bin/echo", "hello"])
        self.assertEqual(uid, None)
        self.assertEqual(gid, None)
        self.assertIn("NCOLONY_CONFIG", env)
        self.assertEqual(env["NCOLONY_CONFIG"], message)
        env.pop("NCOLONY_CONFIG")
        self.assertIn("NCOLONY_NAME", env)
        self.assertEqual(env["NCOLONY_NAME"], "hello")
        env.pop("NCOLONY_NAME")
        self.assertEqual(env, {})
        self.assertEqual(self.logMessages, ["Added monitored process: hello"])

    def test_add_complicated(self):
        """Test a process addition with all the optional arguments"""
        message = helper.dumps2utf8(
            dict(args=["/bin/echo", "hello"], uid=0, gid=0, env={"world": "616"})
        )
        self.receiver.add("hello", message)
        self.assertEqual(len(self.monitor.events), 1)
        ((tp, name, args, uid, gid, env),) = self.monitor.events
        self.assertEqual(tp, "ADD")
        self.assertEqual(name, "hello")
        self.assertEqual(args, ["/bin/echo", "hello"])
        self.assertEqual(uid, 0)
        self.assertEqual(gid, 0)
        self.assertIn("NCOLONY_CONFIG", env)
        self.assertEqual(env["NCOLONY_CONFIG"], message)
        env.pop("NCOLONY_CONFIG")
        env.pop("NCOLONY_NAME")
        self.assertEqual(env, {"world": "616"})
        self.assertEqual(self.logMessages, ["Added monitored process: hello"])

    def test_add_with_junk(self):
        """Test a process addition with all the optional arguments"""
        message = helper.dumps2utf8(dict(something=1, args=["/bin/echo", "hello"]))
        self.receiver.add("hello", message)
        self.assertEqual(len(self.monitor.events), 1)
        ((tp, name, args, uid, gid, env),) = self.monitor.events
        self.assertEqual(tp, "ADD")
        self.assertEqual(name, "hello")
        self.assertEqual(args, ["/bin/echo", "hello"])
        self.assertEqual(uid, None)
        self.assertEqual(gid, None)
        self.assertIn("NCOLONY_CONFIG", env)
        self.assertEqual(env["NCOLONY_CONFIG"], message)
        self.assertEqual(self.logMessages, ["Added monitored process: hello"])
        env.pop("NCOLONY_CONFIG")
        env.pop("NCOLONY_NAME")
        self.assertEqual(env, {})
        self.assertEqual(self.logMessages, ["Added monitored process: hello"])

    def test_add_with_inherited_env(self):
        """Test a process addition with all the optional arguments"""
        small_environment = dict(PATH="123", PYTHONPATH="456")
        receiver = process_events.Receiver(self.monitor, small_environment)
        message = helper.dumps2utf8(
            dict(args=["/bin/echo", "hello"], env_inherit=["PATH"])
        )
        receiver.add("hello", message)
        self.assertEqual(len(self.monitor.events), 1)
        ((tp, name, args, uid, gid, env),) = self.monitor.events
        self.assertEqual(tp, "ADD")
        self.assertEqual(name, "hello")
        self.assertEqual(args, ["/bin/echo", "hello"])
        self.assertEqual(uid, None)
        self.assertEqual(gid, None)
        self.assertIn("NCOLONY_CONFIG", env)
        self.assertEqual(env["NCOLONY_CONFIG"], message)
        self.assertEqual(self.logMessages, ["Added monitored process: hello"])
        env.pop("NCOLONY_CONFIG")
        env.pop("NCOLONY_NAME")
        sent_environment = small_environment.copy()
        sent_environment.pop("PYTHONPATH")
        self.assertEqual(env, sent_environment)
        self.assertEqual(self.logMessages, ["Added monitored process: hello"])

    def test_remove(self):
        """Test a process removal"""
        message = helper.dumps2utf8(dict(args=["/bin/echo", "hello"]))
        self.receiver.add("hello", message)
        self.receiver.remove("hello")
        self.assertEqual(self.monitor.events[-1], ("REMOVE", "hello"))
        self.assertEqual(self.logMessages[-1], "Removed monitored process: hello")

    def test_restart(self):
        """Test a process restart"""
        message = helper.dumps2utf8(dict(type="RESTART", name="hello"))
        self.receiver.message(message)
        self.assertEqual(self.monitor.events, [("RESTART", "hello")])
        self.assertEqual(self.logMessages, ["Restarting monitored process: hello"])

    def test_unknown_message(self):
        """Test that we reject unknown messages"""
        message = helper.dumps2utf8(dict(type="LALALA", name="goodbye"))
        with self.assertRaises(ValueError):
            self.receiver.message(message)

    def test_restart_all(self):
        """Test a global restart"""
        message = helper.dumps2utf8(dict(type="RESTART-ALL"))
        self.receiver.message(message)
        self.assertEqual(self.monitor.events, [("RESTART-ALL",)])
        self.assertEqual(self.logMessages, ["Restarting all monitored processes"])

    def test_restart_group(self):
        """Restarting group of one restarts the process in group"""
        message = helper.dumps2utf8(dict(args=["/bin/echo", "hello"], group=["things"]))
        self.receiver.add("hello", message)
        message = helper.dumps2utf8(dict(type="RESTART-GROUP", group="things"))
        self.receiver.message(message)
        self.assertEqual(self.monitor.events[-1], ("RESTART", "hello"))

    def test_restart_empty_group(self):
        """Restarting empty group restarts no processes"""
        message = helper.dumps2utf8(dict(args=["/bin/echo", "hello"], group=["things"]))
        self.receiver.add("hello", message)
        self.receiver.remove("hello")
        message = helper.dumps2utf8(dict(type="RESTART-GROUP", group="things"))
        self.receiver.message(message)
        self.assertNotEqual(self.monitor.events[-1][0], "RESTART")
