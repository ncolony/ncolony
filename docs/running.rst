Running NColony
===============

In this section, we assume everything to be running in an
environment where "pip install ncolony" has taken place.
This will usually be a virtualenv, which should be activated.

Example
-------

We want to run the demo Twisted web server
and, periodically,
echo hello.
Those are maybe not useful to run,
but they will serve as an example.

The following commands will do that:

.. code::

    $ mkdir /messages /conf
    $ python -m ncolony ctl --messages /messages --config /conf add \
                --name=web \
                --cmd=python --arg=-m --arg=twisted --arg=web
    $ python -m ncolony ctl --messages /messages --config /conf add \
                --name=echo \
                --cmd=python --arg=-m --arg=twisted --arg=ncolony-scheduler \
                --arg=--arg=echo --arg=--arg=hello \
                --arg=--frequency=10 --arg=--timeout=5 --arg=--grace=10
    $ python -m twisted ncolony --messages /messages --config /conf

This is pretty dense, but it can be broken down into parts.
We will not go in order,
but rather in pedagogical order.

.. code::

    $ mkdir /messages /conf

This is the easiest -- it makes sure the directories that will
hold the configuration of ncolony.

We end with

.. code::

    $ python -m twisted ncolony --messages /messages --config /conf

which runs the ncolony supervisor.

The commands in the middle change (in this case, add)
ncolony configuration.
There are three ways to change ncolony configuration:

* Command-line using :code:`python -m ncolony ctl`.
* API using :code:`ncolony.ctllib`.
* Direct JSON-format file manipulation in :code:`/conf' or :code:`/messages`.

Note that all three ways are equivalent,
and should be used in different situations.
The demonstration here uses the command-line access:
this is also useful for configuration-management systems like SaltStack,
or build configurations like Dockerfile.

The first command configuration,
for the Twisted demo web server:

.. code::

    $ python -m ncolony ctl --messages /messages --config /conf add\
                --name=web \
                --cmd=python --arg=-m --arg=twisted --arg=web

The first (physical) line will sometimes be in an alias
or in some other kind of variable --
depending on the system using to run that command.
In our case,
for explanatory reasons,
we repeat it in full.

These arguments to :code:`ctl`
(:code:`--messages` and :code:`--config`)
are the same as the ones to :code:`python -m twisted ncolony`.
This allows multiple ncolony managers to run without
clashing: control is based on the directories where the files
are kept. 

The next physical line has the logical name of the process.
It is important that it be distinct --
:code:`add` of the same name is interpreted as an update to the process
parameters --
for example, if ncolony is already running,
it will cause a restart of the process.

The next line actually has the parameters.
While there are more possible parameters
(for example, to set environment variables or user to run as)
the command line arguments are the most popular.

While ncolony can be used to run any process,
in any language,
here we use it to run a Twisted-based Python web server.
Therefore, the "command" is Python, and the parameters
will make it equivalent to run :code:`python -m twisted web` --
which, when given no parameters,
will run the demo web server.


The periodic process is more complicated:

.. code::

    $ python -m ncolony ctl --messages /messages --config /conf add\
                --name=echo \
                --cmd=python --arg=-m --arg=twisted --arg=ncolony-scheduler \
                --arg=--arg=echo --arg=--arg=hello \
                --arg=--frequency=10 --arg=--timeout=5 --arg=--grace=10


NColony is designed to run long-lived processes --
not a short-lived process that,
says,
writes something to standard output and then exits.
The service :code:`ncolony-scheduler` is designed to bridge that gap:
it will manage the short-lived process,
and ncolony just has to monitor the service,
which is long-lived.

So we use :code:`python -m ncolony ctl` to add an :code:`ncolony-scheduler`
service that will run :code:`echo hello` every 10 seconds --
give it 5 seconds before terminating it,
and 10 seconds before killing it unignorably.

If we need to restart the web process, we can run

.. code::

    $ python -m ncolony ctl --messages /messages --config /conf restart \
                --name=echo

We can also restart everything with 

    $ python -m ncolony ctl --messages /messages --config /conf restart-all


The :code:`/conf` directory holds the configuration --
which processes need to be run,
and some metadata about them.
The :code:`/messages` directory is where messages to the ncolony
process are kept, until they are handled --
for example, a request to restart a process will be there
until it is handled.

It is important to note that it does not matter what order
we run these in. In fact, if we now shut down (via CTRL-C)
the ncolony monitor, and start it again, it will start the
same programs again.

:command:`python -m twisted` Command-Line Options
===========--------------------------------------

A full set of twistd command-line options can be found in the
:code:`python -m twisted` help (available via :command:`python -m twisted --help`).

:command:`python -m twisted ncolony` Command-Line Options
---------------------------------------------------------

Option: --config DIR
    Directory for configuration

Option: --messages DIR
    Directory for messages

Option: --frequency SECONDS
    Frequency of checking for updates [default: 10]

Option: --pid DIR
    Directory of PID files.
    If not given, no PID files will be written.
    In general, PID files are not necessary,
    unless we want something to be able to recover
    from a crash of the ncolony manager itself.

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

:command:`python -m ncolony ctl` Command-Line Options
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

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

:command:`python -m ncolony ctl add` Command-Line Options
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

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
the :code:`python -m twisted` log configuration.
Additionally :code:`ncolony` will log processes' stdout/err.

