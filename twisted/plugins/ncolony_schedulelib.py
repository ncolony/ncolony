# Copyright (c) Moshe Zadka
# See LICENSE for details.
from twisted.application.service import ServiceMaker
	
serviceMaker = ServiceMaker(
    "ncolony Scheduler",
    "ncolony.schedulelib",
    "A command-line scheduler",
    "ncolonysched",
)
