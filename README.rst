.. Copyright (c) Moshe Zadka
   See LICENSE for details.

NColony
-------

Infrastructure for running "colonies" of processes.

.. image:: https://travis-ci.org/moshez/ncolony.svg?branch=master
    :target: https://travis-ci.org/moshez/ncolony

.. image:: https://readthedocs.org/projects/ncolony/badge/?version=latest
    :alt: Documentation Status
    :scale: 100%
    :target: https://readthedocs.org/projects/ncolony/

Hacking
=======

  $ tox

Should DTRT -- if it passes, it means
unit tests are passing, and 100% coverage.
Note that Travis-CI will automatically run tests on pull requests.

Please feel free to submit pull requests which are failing.
However,
they cannot be merged until the they are green in Travis-CI.

Release
========

* Checkout a new branch
* Run :code:`python -m incremental.update ncolony` to rev the number.
* Create a pull request
* Merge the pull request
* Run :code:`tox`
* Take the wheel and the sdist from build/tox, and use :code:`twine` to upload
  them

Contributors
=============

Moshe Zadka <zadka.moshe@gmail.com>
Mark Williams

License
=======

MIT License
