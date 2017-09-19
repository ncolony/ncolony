.. Copyright (c) Moshe Zadka
   See LICENSE for details.

NColony
=======

NColony is a process monitor.
It starts processes,
and restarts them when they die,
or when asked to.

NColony is a Python package available from PyPI_,
and developed on GitHub_.
It is based on Twisted_,
and works on both Python 2 and Python 3.

NColony is guided by the following principles:

* Commitment to code quality:
  we use code reviews,
  unit testing,
  integration testing,
  and static checking to increase the quality of our code.
* Different domains in different processes:
  the main NColony daemon just starts, shuts down, and restarts processes.
  Other concerns,
  such as health checking and network control,
  are handled by other processes --
  optionally managed by NColony.
* Run processes directly as children,
  to avoid race-condition-prone :code:`pid` file mechanisms for monitoring.

Since NColony should be reliable,
seeing as how it is monitoring other processes,
the hope is that by keeping the code small and high quality,
we can make it as stable as possible.

NColony is developed under a `Code of Conduct`,
inspired by the `Contributor covenant`_.

.. _PyPI: https://pypi.python.org/pypi/ncolony
.. _GitHub: https://github.com/moshez/ncolony
.. _Twisted: https://twistedmatrix.com
.. _Code of Conduct: https://github.com/moshez/ncolony/blob/master/covenant.rst
.. _Contributor convenant: https://www.contributor-covenant.org/


.. toctree::
   :maxdepth: 2

   introduction
   running
   configuration
   process
   api
