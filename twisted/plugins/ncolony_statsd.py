# Copyright (c) Moshe Zadka
# See LICENSE for details.

"""Plugin for ncolony statsd twistd service"""

from twisted.application.service import ServiceMaker

serviceMaker = ServiceMaker(
    "ncolony statsd server",
    "ncolony.statsd",
    "A statistics aggregator",
    "ncolony-statsd",
)
