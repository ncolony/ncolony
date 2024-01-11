# Copyright (c) Moshe Zadka
# See LICENSE for details.

"""Plugin for ncolony supervisor twistd service"""

from twisted.application.service import ServiceMaker

serviceMaker = ServiceMaker(
    "ncolony Process Supervisor",
    "ncolony.service",
    "A process supervisor with file-based control",
    "ncolony",
)
