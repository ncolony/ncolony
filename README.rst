.. Copyright (c) Moshe Zadka
   See LICENSE for details.

Synopsis
=========

EXPERIMENTAL EXPERIMENTAL EXPERIMENTAL
YOU SHOULD PROBABLY NOT USE IT IN PRODUCTION!!!
THIS CODE IS EXTREMELY UNTESTED

NColony: Infrastructure for running "colonies" of processes.

Code Example
=========

Assuming an environment where 'pip install ncolony' has been done

  $ DEFAULT="--config config --messages messages"
  $ twistd ncolony $DEFAULT
  $ python -m ncolony.ctl $DEFAULT add sleeper --cmd=/bin/sleep --arg=10
  $ python -m ncolony.ctl $DEFAULT restart sleeper

Installation
=========

For deployment in production:
  $ pip install ncolony

API Reference
=========

TBD

Tests
=========

The following will set up your development environment and run the unit and functional tests.
 $ ./setup-dev && ./runtests && ./functional-test 

Contributors
=========

Moshe Zadka <zadka.moshe@gmail.com>

License
=======

MIT License
