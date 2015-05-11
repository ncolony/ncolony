import unittest

from twisted.internet import task

from ncolony.client import statsd

class TestFormatter(unittest.TestCase):

    def setUp(self):
        self.format = statsd._format

    def test_format_incr_empty(self):
        res = self.format('hits.home', 'incr', None, None)
        self.assertEquals(res, 'hits.home:1|c')

    def test_format_incr_explicit(self):
        res = self.format('hits.home', 'incr', 3, None)
        self.assertEquals(res, 'hits.home:3|c')

    def test_format_incr_empty_prefix(self):
        res = self.format('hits.home', 'incr', None, 'froop')
        self.assertEquals(res, 'froop.hits.home:1|c')

    def test_format_incr_explicit_prefix(self):
        res = self.format('hits.home', 'incr', 2, 'froop')
        self.assertEquals(res, 'froop.hits.home:2|c')

    def test_format_decr_empty(self):
        res = self.format('hits.home', 'decr', None, None)
        self.assertEquals(res, 'hits.home:-1|c')

    def test_format_decr_explicit(self):
        res = self.format('hits.home', 'decr', 3, None)
        self.assertEquals(res, 'hits.home:-3|c')

    def test_format_decr_empty_prefix(self):
        res = self.format('hits.home', 'decr', None, 'froop')
        self.assertEquals(res, 'froop.hits.home:-1|c')

    def test_format_decr_explicit_prefix(self):
        res = self.format('hits.home', 'decr', 2, 'froop')
        self.assertEquals(res, 'froop.hits.home:-2|c')

    def test_format_timing_empty(self):
        with self.assertRaises(ValueError):
            self.format('hits.latency', 'timing', None, None)

    def test_format_timing_explicit(self):
        res = self.format('hits.latency', 'timing', 3, None)
        self.assertEquals(res, 'hits.latency:3|ms')

    def test_format_timing_empty_prefix(self):
        with self.assertRaises(ValueError):
            self.format('hits.latency', 'timing', None, 'froop')

    def test_format_timing_explicit_prefix(self):
        res = self.format('hits.latency', 'timing', 2, 'froop')
        self.assertEquals(res, 'froop.hits.latency:2|ms')

    def test_format_set_empty(self):
        with self.assertRaises(ValueError):
            self.format('hits.url', 'set', None, None)

    def test_format_set_explicit(self):
        res = self.format('hits.things', 'set', 4, None)
        self.assertEquals(res, 'hits.things:4|s')

    def test_format_set_empty_prefix(self):
        with self.assertRaises(ValueError):
            self.format('hits.things', 'set', None, 'froop')

    def test_format_set_explicit_prefix(self):
        res = self.format('hits.things', 'set', 4, 'froop')
        self.assertEquals(res, 'froop.hits.things:4|s')

    def test_format_gauge_delta_empty(self):
        with self.assertRaises(ValueError):
            self.format('hits.url', 'gaugeDelta', None, None)

    def test_format_gauge_delta_explicit(self):
        res = self.format('memory.pages', 'gaugeDelta', 4, None)
        self.assertEquals(res, 'memory.pages:+4|g')

    def test_format_gauge_delta_explicit_negative(self):
        res = self.format('memory.pages', 'gaugeDelta', -4, None)
        self.assertEquals(res, 'memory.pages:-4|g')

    def test_format_gauge_delta_empty_prefix(self):
        with self.assertRaises(ValueError):
            self.format('hits.things', 'gaugeDelta', None, 'froop')

    def test_format_gauge_delta_explicit_prefix(self):
        res = self.format('memory.pages', 'gaugeDelta', 4, 'froop')
        self.assertEquals(res, 'froop.memory.pages:+4|g')

    def test_format_gauge_set_empty(self):
        with self.assertRaises(ValueError):
            self.format('hits.url', 'gaugeSet', None, None)

    def test_format_gauge_set_explicit(self):
        res = self.format('memory.pages', 'gaugeSet', 4, None)
        self.assertEquals(res, 'memory.pages:4|g')

    def test_format_gauge_set_explicit_negative(self):
        res = self.format('memory.pages', 'gaugeSet', -4, None)
        self.assertEquals(res, 'memory.pages:0|g\nmemory.pages:-4|g')

    def test_format_gauge_set_empty_prefix(self):
        with self.assertRaises(ValueError):
            self.format('hits.things', 'gaugeSet', None, 'froop')

    def test_format_gauge_set_explicit_prefix(self):
        res = self.format('memory.pages', 'gaugeSet', 4, 'froop')
        self.assertEquals(res, 'froop.memory.pages:4|g')

class TestPipeline(unittest.TestCase):

    def setUp(self):
        def testNoLeftovers():
            delayed = self.clock.getDelayedCalls()
            self.assertEquals(list(delayed), [])
        self.addCleanup(testNoLeftovers)
        self.clock = task.Clock()

    def test_build_pipeline(self):
        write = lambda s: None
        pipeline = statsd._Pipeline(originalWrite=write, maxsize=513, delay=0.213, reactor=self.clock)
        self.assertIs(pipeline.originalWrite, write)
        self.assertEquals(pipeline.maxsize, 513)
        self.assertEquals(pipeline.delay, 0.213)
        self.assertIs(pipeline.reactor, self.clock)
        self.assertEquals(pipeline.outstanding, None)
        self.assertEquals(pipeline.buffer, '')
        for attr in ('originalWrite', 'maxsize', 'delay', 'reactor'):
            with self.assertRaises(AttributeError):
                setattr(pipeline, attr, getattr(pipeline, attr))

    def test_one_write(self):
        written = []
        pipeline = statsd._Pipeline(originalWrite=written.append, maxsize=513, delay=0.213, reactor=self.clock)
        pipeline.write('hello')
        self.assertEquals(written, [])
        self.clock.advance(0.25)
        self.assertEquals(written, ['hello'])

    def test_simple_flush(self):
        written = []
        pipeline = statsd._Pipeline(originalWrite=written.append, maxsize=513, delay=0.213, reactor=self.clock)
        pipeline.write('a'*512)
        pipeline.write('b'*10)
        self.assertEquals(written, ['a'*512])
        self.clock.advance(0.3)
        self.assertEquals(written, ['a'*512, 'b'*10])

    def test_no_incremenetal_delay(self):
        written = []
        pipeline = statsd._Pipeline(originalWrite=written.append, maxsize=513, delay=5, reactor=self.clock)
        pipeline.write('a')
        self.assertEquals(written, [])
        self.clock.advance(4)
        pipeline.write('b')
        self.clock.advance(2)
        self.assertEquals(written, ['ab'])

    def test_write_eventually(self):
        written = []
        pipeline = statsd._Pipeline(originalWrite=written.append, maxsize=513, delay=5, reactor=self.clock)
        pipeline.write('a')
        self.assertEquals(written, [])
        self.clock.advance(10)
        self.assertEquals(written, ['a'])
        pipeline.write('b')
        self.clock.advance(10)
        self.assertEquals(written, ['a', 'b'])
