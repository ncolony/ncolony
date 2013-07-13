#!/usr/bin/env python
import re
from distutils.core import setup

package = file("support/package").read().strip()
packageObj = __import__(package)

long_description = file("README").read()
firstLine = long_description.splitlines()[0]
name, description = firstLine.split(": ")
firstAuthor = file("CREDITS").readline()
authorRE = re.compile("^([A-Za-z ]+) <([^>]*)>")
match = authorRE.match(firstAuthor)
author, author_email = match.groups()

setup(name=name,
      version=packageObj.__version__,
      description=description,
      author=author,
      author_email=author_email,
      long_description=long_description,
      license="BSD 2 Clause",
      url='http://example.com/',
      packages=[''],
      scripts=['bin/ncexec'],
)
