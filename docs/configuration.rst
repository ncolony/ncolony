Configuration
=============

The ncolony configuration is stored in a directory, :code:`conf`.
There is no default -- this directory needs to be passed explicitly
to the ncolony server as well as to the control command.

The usual command to modify this configuration is
:command:`python -m ncolony ctl add`
(although :code:`remove` is also useful, of course).
In order to modify a command, add should be called with the
same name. 
NColony will automatically restart the command when its configuration
changes.

Examples
--------

Running Sentry_:

.. code::

    $ python -m ncolony ctl add sentry --cmd /myvenv/bin/sentry \
        --arg start --arg --config=/etc/sentry.conf

or

.. code::

    from ncolony import ctllib

    ctllib.add(name='sentry', cmd='/myvenv/bin/sentry',
               args=['start', '--config=/etc/sentry.conf'])

Running a Twisted demo server:

.. code::

    $ python -m ncolony ctl add demo-server --cmd /myvenv/bin/twistd \
        --arg --nodaemon --arg web

or

.. code::

   $ python -m ncolony ctl add demo-server -- /myvenv/bin/twistd \
        --nodaemon web

or, with the Python API,

.. code::

    from ncolony import ctllib

    ctllib.add(name='demo-server', cmd='/myvenv/bin/twistd',
               args=['--nodaemon', 'web'])

Note the :code:`--nodaemon`: programs run by ncolony should not daemonize,
so that ncolony can properly monitor them.

.. _Sentry: https://getsentry.com/welcome/
