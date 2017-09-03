# Copyright (c) Moshe Zadka
# See LICENSE for details.

"""Test the directory monitoring code"""

import os
import shutil
import unittest

from zope import interface
from zope.interface import verify

from ncolony import directory_monitor
from ncolony import interfaces

@interface.implementer(interfaces.IMonitorEventReceiver)
class EventRecorder(object):

    """An event receiver that just records the events"""

    def __init__(self):
        """Initialize the event list"""
        self.events = []

    def add(self, name, contents):
        """Get an add event"""
        self.events.append(('ADD', name, contents))

    def remove(self, name):
        """Get a remove event"""
        self.events.append(('REMOVE', name))

    def message(self, contents):
        """Get a new message event"""
        self.events.append(('MESSAGE', contents))

## pylint: disable=too-few-public-methods
@interface.implementer(interfaces.IMonitorEventReceiver)
class EventRecorderNoAdd(object):

    """Dummy bad implementation of event receiver interface"""

    def remove(self, name):
        """Dummy remove method"""
        pass

@interface.implementer(interfaces.IMonitorEventReceiver)
class EventRecorderNoRemove(object):

    """Dummy bad implementation of event receiver interface"""

    def add(self, name, content):
        """Dummy add method"""
        pass
## pylint: enable=too-few-public-methods


class TestReceiverIface(unittest.TestCase):

    """Test that the right classes implement the interface"""

    def test_recorder_is_good(self):
        """Test our recorder implements the interface"""
        self.assertTrue(verify.verifyObject(interfaces.IMonitorEventReceiver, EventRecorder()))

    def test_no_add_bad(self):
        """Test you need 'add' to implement the interface"""
        with self.assertRaises(verify.BrokenImplementation):
            verify.verifyObject(interfaces.IMonitorEventReceiver, EventRecorderNoAdd())

    def test_no_remove_bad(self):
        """Test you need 'remove' to implement the interface"""
        with self.assertRaises(verify.BrokenImplementation):
            verify.verifyObject(interfaces.IMonitorEventReceiver, EventRecorderNoRemove())


class DirectoryBasedTest(unittest.TestCase):

    """Base class for directory-based tests"""

    def setUp(self):
        """Initialize/cleanup the directory"""
        self.testDirectory = os.path.join(os.getcwd(), 'stuff')
        def _cleanup():
            if os.path.exists(self.testDirectory):
                shutil.rmtree(self.testDirectory)
        self.addCleanup(_cleanup)
        _cleanup()
        os.makedirs(self.testDirectory)

    def write(self, name, content):
        """Write a file in the directory"""
        name = os.path.join(self.testDirectory, name)
        with open(name, 'wb') as fp:
            fp.write(content)

    def remove(self, name):
        """Remove a file from the directory"""
        name = os.path.join(self.testDirectory, name)
        os.remove(name)

class TestMessageSender(DirectoryBasedTest):

    """Test monitoring the messages directory"""

    def setUp(self):
        """Set up test"""
        DirectoryBasedTest.setUp(self)
        self.receiver = EventRecorder()
        self.message = directory_monitor.messages(self.testDirectory, self.receiver)
        self.assertFalse(self.receiver.events)

    def test_nada(self):
        """Test no messages"""
        self.message()
        self.assertFalse(self.receiver.events)

    def test_ignore_new(self):
        """Test ignoring messages with .new extension"""
        self.write('00Message.new', b'hello')
        self.message()
        self.assertFalse(self.receiver.events)

    def test_one_message(self):
        """Test processing one message"""
        self.write('00Message', b'hello')
        self.message()
        self.assertEquals(self.receiver.events, [('MESSAGE', b'hello')])
        self.message()
        self.assertEquals(self.receiver.events, [('MESSAGE', b'hello')])

    def test_repeated_message(self):
        """Test the same message repeated twice"""
        self.write('00Message', b'hello')
        self.message()
        self.assertEquals(self.receiver.events, [('MESSAGE', b'hello')])
        self.write('00Message', b'hello')
        self.message()
        self.assertEquals(self.receiver.events, [('MESSAGE', b'hello'),
                                                 ('MESSAGE', b'hello')])

    def test_changed_message(self):
        """Test the same message name with different contents"""
        self.write('00Message', b'hello')
        self.message()
        self.assertEquals(self.receiver.events, [('MESSAGE', b'hello')])
        self.write('00Message', b'goodbye')
        self.message()
        self.assertEquals(self.receiver.events, [('MESSAGE', b'hello'),
                                                 ('MESSAGE', b'goodbye')])


class TestEventSender(DirectoryBasedTest):

    """Test monitoring the configuration directory"""

    def setUp(self):
        """Set up the test"""
        DirectoryBasedTest.setUp(self)
        self.receiver = EventRecorder()
        self.monitor = directory_monitor.checker(self.testDirectory, self.receiver)
        self.assertFalse(self.receiver.events)

    def test_nada(self):
        """Test empty configuration"""
        self.monitor()
        self.assertFalse(self.receiver.events)

    def test_ignore_new(self):
        """Test ignoring a file with a .new extension"""
        self.write('one.new', b'A')
        self.monitor()
        self.assertFalse(self.receiver.events)

    def test_one_add(self):
        """Test one file in the configuration"""
        self.write('one', b'A')
        self.monitor()
        self.assertEquals(self.receiver.events, [('ADD', 'one', b'A')])

    def test_redundant_check(self):
        """Test one file in the configuration and no changes"""
        self.write('one', b'A')
        self.monitor()
        self.monitor()
        self.assertEquals(self.receiver.events, [('ADD', 'one', b'A')])

    def test_non_redundant_check(self):
        """Test one file in the configuration and then a change"""
        self.write('one', b'A')
        self.monitor()
        self.write('two', b'B')
        self.monitor()
        self.assertEquals(self.receiver.events, [('ADD', 'one', b'A'),
                                                 ('ADD', 'two', b'B')])

    def test_remove(self):
        """Test one file in the configuration and then removed"""
        self.write('one', b'A')
        self.monitor()
        self.remove('one')
        self.monitor()
        self.assertEquals(self.receiver.events, [('ADD', 'one', b'A'),
                                                 ('REMOVE', 'one')])

    def test_change(self):
        """Test one file in the configuration and then changed"""
        self.write('one', b'A')
        self.monitor()
        self.write('one', b'B')
        self.monitor()
        self.assertEquals(self.receiver.events, [('ADD', 'one', b'A'),
                                                 ('REMOVE', 'one'),
                                                 ('ADD', 'one', b'B')])
