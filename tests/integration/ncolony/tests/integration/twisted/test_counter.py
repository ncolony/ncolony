# Copyright (C) 2013 -- see CREDITS for copyright holders, LICENSE for license
"""
Basic HTTP-based integration test
"""
import logging

from ncolony.tests.integration import counter

LOG = logging.getLogger(__name__)

class RestTestCase(counter.AbstractRestTestCase):
  __test__ = True
  style = 'twisted'
