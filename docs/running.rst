Running NColony
===============

In this section, we assume everything to be running in an
environment where "pip install ncolony" has taken place.
This will usually be a virtualenv, which should be activated.

Running ncolony monitor
-----------------------

Create two directories: :code:`conf` and :code:`messages`.
For simplicity, we will assume that they live in the root directory,
:code:`/` -- :code:`/conf/` and :code:`/messages/`.

.. code::

    twistd -n ncolony --messages /messages --config /conf

Of course, it is useless to run a monitor without any processes
to monitor:

.. code::

    python -m ncolony ctl --messages /messages --config /conf add \
                      my-cat-program --cmd cat

This will add the cat program as a monitored program.
Because :code:`cat` hangs forever reading from stdin,
it will never die.
It is important to note that it does not matter what order
we run these in. In fact, if we now shut down (via CTRL-C)
the ncolony monitor, and start it again, it will start the
:code:`cat` program again.

:command:`twistd` Command-Line Options
--------------------------------------

A full set of twistd command-line options can be found in the
twistd help (available via :command:`twistd --help`).

:command:`twistd ncolony` Command-Line Options
----------------------------------------------

Option: --config DIR
    Directory for configuration

Option: --messages DIR
    Directory for messages

Option: --frequency SECONDS
    Frequency of checking for updates [default: 10]

Option: --pid DIR
    Directory of PID files

Option: -t SECONDS, --threshold SECONDS
    How long a process has to live before the death is
    considered instant, in seconds. [default: 1]

Option: -k SECONDS, --killtime SECONDS
    How long a process being killed has to get its affairs
    in order before it gets killed with an unmaskable
    signal. [default: 5]

Option: -m SECONDS, --minrestartdelay SECONDS
    The minimum time (in seconds) to wait before
    attempting to restart a process [default: 1]

Option: -M SECONDS, --maxrestartdelay SECONDS
    The maximum time (in seconds) to wait before
    attempting to restart a process [default: 3600]

:command:`python -m ctl` Command-Line Options
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The following must be given before the subcommand:

Option: --messages DIR
    directory of NColony monitor messages
Option: --config DIR
    directory of NColony monitor configuration

The following follow the subcommand:

restart-all
    Takes no arguments

restart, remove
    Only one positional argument -- name of program

:command:`python -m ctl add` Command-Line Options
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Option: --cmd CMD
    Name of executable

Option: --arg ARGS
    Add an argument to the command

Option: --env NAME=VALUE
   Add an environment variable

Option: --uid UID
   Run as given user id (only useful
   if ncolony monitor is running as root)

Option: --gid GID
   Run as given group id (only useful
   if ncolony monitor is running as root)

Option: --extras EXTRAS
   a JSON-encoded dictionary with extra
   configuration parameters. Those are not
   used by the monitor itself, but are
   available to the running program
   (as the variable NCOLONY_CONFIG)
   and to other programs which scan the
   configuration directory.

For programmatic access, it is recommended
to use the :code:`ncolony.ctllib` module
from a Python program instead of passing
arguments to a :code:`python -m ncolony ctl`
subprocess.

Logging
~~~~~~~

The log of :code:`ncolony` itself is configured by using
the :code:`twistd` log configuration.
While :code:`ncolony` will log processes' stdout/err,
it is highly encouraged to set logs for these.
Ideally, :code:`ncolony` logs should also show either
catastrophic errors in processes, such that even the
log could not be opened,
or messages that are sent before the log is set.
