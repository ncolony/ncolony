Running processes
=================

Nondaemonizing
--------------

Just like Supervisor_ and Daemontools_, NColony assumes
that the processes it runs do not daemonize.
While many servers will daemonize by default,
it is often possible to keep them in the foreground
by passing the right command-line options
or setting the right configuration file variables.

When configuring an ncolony command,
first try running it from the command-line.
If the prompt returns immediately
(or, indeed, at all unless the program unexpectedly crashed)
that means the program daemonizes itself.

Supervisor and Daemontools both have many
resources about how to achieve that properly.
There are also examples in `The DJB Way`_.
While both of these also come with work-around scripts
that try to de-daemonize processes,
both approaches are fundamentally broken.
Not through any lack of effort by the authors,
but because it is impossible to solve it correctly.
NColony takes the purist tack that these things
should be solved at the daemon level.

If working around those problems is important enough,
it is possible to install fghack or pidproxy in order
to semi-un-daemonize servers.

Environment
-----------

Processes will be run in an environment composed of:

 * Environment variables explicitly requested by :code:`add`
 * :code:`NCOLONY_NAME` (name of the process)
 * :code:`NCOLONY_CONFIG` (JSON-encoded configuration passed to ncolony itself)

Note that the environment that ncolony runs under will not be inherited,
and no other variables are automatically set.
In particular, if :code:`USER` or :code:`HOME` are needed,
they should be passed explicitly by :code:`add`.

.. _Daemontools: http://cr.yp.to/daemontools/faq/create.html#fghack
.. _Supervisor: http://supervisord.org/subprocess.html#nondaemonizing-of-subprocesses
.. _The DJB Way: http://thedjbway.b0llix.net/services.html
