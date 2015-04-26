.. Copyright (c) Moshe Zadka
   See LICENSE for details.

Ncolony
-------

Infrastructure for running "colonies" of processes.

.. image:: https://travis-ci.org/moshez/ncolony.svg?branch=master
    :target: https://travis-ci.org/moshez/ncolony

.. image:: https://readthedocs.org/projects/ncolony/badge/?version=latest
    :alt: Documentation Status
    :scale: 100%
    :target: https://readthedocs.org/projects/ncolony/

Please note that this is still experimental,
and has not been tested in production.

Hacking
=======

  $ tox

Should DTRT -- if it passes, it means
unit tests are passing, and 100% coverage.

Example
========

Assuming an environment where 'pip install ncolony' has been done

.. code-block:: bash

  $ DEFAULT="--config config --messages messages"
  $ twistd ncolony $DEFAULT
  $ python -m ncolony.ctl $DEFAULT add sleeper --cmd=/bin/sleep --arg=10
  $ python -m ncolony.ctl $DEFAULT restart sleeper

Contributors
=============

Moshe Zadka <zadka.moshe@gmail.com>

License
=======

MIT License
