Docker
======

NColony is often used in Docker containers.
In order to illustrate this,
we include here a "serving suggestion"
of how to use NColony in a container.
This example uses an NColony source checkout --
but one character can change it to using
the latest version from PyPI.

We start by using an Python 3 image
which contains build tools,
in order to build wheels:

.. literalinclude:: example.docker
    :lines: 1

We set up the place the wheels will go,
Since NColony needs :code:`incremental`
at setup time,
it needs to be manually installed ahead of time --
otherwise the :code:`setup.py` file fails to load.

.. literalinclude:: example.docker
    :lines: 2-3

We copy the relevant source files into the image.
Note that this step is only needed for building a container
based off of the Git checkout of NColony --
they can be skipped if a PyPI version is desired.

.. literalinclude:: example.docker
    :lines: 4-7

Finally,
we build the wheels.
In order to build from the PyPI version,
just replace :code:`/ncolony`
with :code:`ncolony`.

.. literalinclude:: example.docker
    :lines: 8

Now that the wheels are ready,
time to build the production image.
We start,
this time,
from a minimal Python image.

.. literalinclude:: example.docker
    :lines: 10

We copy the wheels over from the previous stage.

.. literalinclude:: example.docker
    :lines: 11

Now we start a big :code:`RUN` command
in order to minimize the number of layers
the production image will have.

First we install the wheels we built
in the previous stage.

.. literalinclude:: example.docker
    :lines: 12

We create the places from which
NColony will read configurations and requests.

.. literalinclude:: example.docker
    :lines: 13-15

Next up,
this is an *example* --
so it is useful to have something running
under NColony.
We choose twisted static file web server.
We create a minimal hierarchy with a "hello world"
HTML file.

.. literalinclude:: example.docker
    :lines: 16-17

Now we configure NColony to run the web server.
This is a typical example of using NColony's
:code:`add` subcommand --
including the length.

.. literalinclude:: example.docker
    :lines: 18-22

Last but not least,
we set up NColony as the entry point.
Since Twisted processes are safe to use as PID 1,
we do not need to use :code:`dumb-init`
(or similar)
as a wrapper.

.. literalinclude:: example.docker
    :lines: 23-
