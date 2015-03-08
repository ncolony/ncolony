# Copyright (c) Moshe Zadka
# See LICENSE for details.

"""Plugin for ncolony scheduler twistd service"""

from twisted.application.service import ServiceMaker

serviceMaker = ServiceMaker(
    "ncolony Scheduler",
    "ncolony.schedulelib",
    "A command-line scheduler",
    "ncolony-scheduler",
)
