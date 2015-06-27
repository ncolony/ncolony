Introduction
============

Overview
~~~~~~~~

NColony is a system to control and monitor a number of processes
on UNIX-like systems. Its primary use-case is to run servers,
and it is specifically optimized to container architectures
like Docker.

Installing
~~~~~~~~~~

The recommended way to install is using virtualenv_ and pip_:

.. code::

    $ python -m virtualenv venv
    $ venv/bin/python -m pip install ncolony

When running other python processes with ncolony,
it is possible to either run them from the ncolony
virtual environment or from a separate virtual environment.

For more options with pip installation, for example for
network-less install, see the pip documentation.

.. _Pip: https://pip.pypa.io/en/stable/
.. _virtualenv: https://virtualenv.pypa.io/en/latest/

NColony components
~~~~~~~~~~~~~~~~~~

NColony is built on the Twisted_ framework.
Most of its parts are implemented as twistd_ plugins,
allowing the end-user to control features like logging,
reactor selection and more.

:program:`twistd ncolony`

  The process monitor is called as the "ncolony" twistd plugin.
  It starts processes, and continuously monitors both process state
  and configuration, and makes sure they are in sync.

  The monitor configuration is a directory with a file per process.
  It also monitors a messages directory with "ephemeral" configuration:
  mostly restart requests.

:program:`twistd ncolony-beatcheck`

  This plugin, intended to be run under the ncolony monitor,
  will look at other processes' configuration,
  check if they are supposed to beat hearts
  (periodically touch a file)
  and message ncolony with a restart request if the heart does
  not beat for too long.

:program:`twistd ncolony-scheduler`

  This plugin, intended to be run under the ncolony monitor,
  will periodically run a short-lived process.
  This allows the main ncolony plugin to assume all of its
  processes are long-lived,
  while still supporting short-lived processes.
  This is useful, e.g., for log-rotation or other periodic
  clean-up tasks.

:program:`python -m ncolony ctl`

  Control program -- add, remove and restart processes.

:program:`python -m ncolony reaper`

  "PID 1". Designed to work with the ncolony monitor
  as a root process in a container environment.
  It is designed to run only one program, and then reap
  any children it adopts.

.. _Twisted: https://twistedmatrix.com/trac/

.. _twistd: http://twistedmatrix.com/documents/current/core/howto/basics.html
