# Copyright (C) 2013 -- see CREDITS for copyright holders, LICENSE for license
#
all: package

clean:
	rm -rf venv var
	find . -name "*.pyc" | xargs -r rm
	rm -f .coverage

venv: support/requirements.txt
	./support/make-venv

test-unit: venv
	./venv/bin/python ./bin/ncexec ./venv/bin/nosetests --where tests/unit --with-coverage --cover-min-percentage=100 --cover-package=`cat support/package`

test-integration: venv
	./venv/bin/python ./bin/ncexec ./venv/bin/nosetests --where tests/integration

test-text: venv
	./venv/bin/python ./support/check-python

test-syntax: venv
	./venv/bin/pylint --rcfile=support/pylintrc `cat support/package`

test-packages: venv
	mkdir -p var
	./venv/bin/pip freeze > var/requirements.txt
	diff -q support/requirements.txt var/requirements.txt

test-git:
	if git status --porcelain | grep '??'; then echo "Untracked files"; false; else true; fi

test: test-unit test-integration test-text test-syntax test-packages test-git

package: venv test
	rm -rf build
	mkdir build
	./venv/bin/python ./bin/ncexec support/setup.py sdist --dist-dir=build --manifest=build/MANIFEST
