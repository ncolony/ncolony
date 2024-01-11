# Copyright (c) Moshe Zadka
# See LICENSE for details.

"""Plugin for ncolony supervisor twistd service"""

from twisted.application.service import ServiceMaker

serviceMaker = ServiceMaker(
    "ncolony health monitor",
    "ncolony.beatcheck",
    "A health monitor for ncolony processes",
    "ncolony-beatcheck",
)
