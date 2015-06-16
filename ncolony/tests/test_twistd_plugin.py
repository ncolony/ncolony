# Copyright (c) Moshe Zadka
# See LICENSE for details.

"""ncolony.tests.test_twistd_plugins

See if the plugins are registered correctly.
"""

import unittest

from ncolony import service, beatcheck, schedulelib

from twisted.plugins import ncolony_service, ncolony_beatcheck, ncolony_schedulelib

class TestServices(unittest.TestCase):

    """Test all registered service makers in ncolony"""

    def test_main_service(self):
        """Options and makeService in main service are correct"""
        sm = ncolony_service.serviceMaker
        self.assertEquals(sm.tapname, 'ncolony')
        self.assertNotEquals(sm.description, '')
        options = sm.options()
        options.parseOptions(['--messages', 'foo', '--config', 'bar'])
        self.assertEquals(options['messages'], 'foo')
        self.assertEquals(options['config'], 'bar')
        self.assertIs(service.makeService, sm.makeService)

    def test_beatcheck_service(self):
        """Options and makeService in beatcheck service are correct"""
        sm = ncolony_beatcheck.serviceMaker
        self.assertEquals(sm.tapname, 'ncolony-beatcheck')
        self.assertNotEquals(sm.description, '')
        options = sm.options()
        options.parseOptions(['--messages', 'foo', '--config', 'bar'])
        self.assertEquals(options['messages'], 'foo')
        self.assertEquals(options['config'], 'bar')
        self.assertIs(beatcheck.makeService, sm.makeService)

    def test_schedulelib_service(self):
        """Options and makeService in scheduler service are correct"""
        sm = ncolony_schedulelib.serviceMaker
        self.assertEquals(sm.tapname, 'ncolony-scheduler')
        self.assertNotEquals(sm.description, '')
        options = sm.options()
        options.parseOptions(['--frequency', '5', '--timeout', '1', '--grace', '1',
                              '--arg', 'cat'])
        self.assertEquals(options['frequency'], 5)
        self.assertEquals(options['args'], ['cat'])
        self.assertIs(schedulelib.makeService, sm.makeService)
