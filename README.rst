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

Release
========

* admin/release <next version number>
* gpg --use-agent -u zadka.moshe@gmail.com --detach-sign --armor dist/*.whl
* gpg --use-agent -u zadka.moshe@gmail.com --detach-sign --armor dist/*.zip
* admin/upload
* Manually verify on testpypi
* admin/upload --prod

Contributors
=============

Moshe Zadka <zadka.moshe@gmail.com>

License
=======

MIT License
