.. Copyright (c) Moshe Zadka
   See LICENSE for details.

## Synopsis

ForepersonD: A wrapper around Twisted process monitor which allows runtime configuration via file-based communication

## Code Example

Assuming an environment where 'pip install ncolony' has been done

  $ DEFAULT="--config config --messages messages"
  $ twistd ncolony $DEFAULT
  $ python -m ncolony.ctl $DEFAULT add sleeper --cmd=/bin/sleep --arg=10
  $ python -m ncolony.ctl $DEFAULT restart sleeper

## Motivation

Twisted has a pretty good process monitor, but the only twistd-based interface to it is something that allows monitoring of only one process specified via the twistd command-line. This is a more sophisticated wrapper, allowing run-time configuration (including forcing restarts of some or all of the processes) via dropping or removing files in pre-designated directories. A simple utility ('python -m ncolony.ctl') is included to allow dropping/removing such files from shell script.

## Installation

For deployment in production:
  $ pip install ncolony

## API Reference

TBD

## Tests

The following will set up your development environment and run the unit and functional tests.
 $ ./setup-dev && ./runtests && ./functional-test 

## Contributors

TBD

## License

MIT License
