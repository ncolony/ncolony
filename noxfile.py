import functools
import os

import nox

nox.options.envdir = "build/nox"
nox.options.sessions = ["lint", "tests", "mypy", "build"]

VERSIONS = ["3.12", "3.11"]


@nox.session(python=VERSIONS)
def func(session):
    tmpdir = session.create_tmp()
    session.install("-r", "requirements-tests.txt")
    session.install("-e", ".")
    session.run(
        *"python -Werror -W ignore::DeprecationWarning -W ignore::ImportWarning -m ncolony.tests.functional_test".split()
    )


@nox.session(python=VERSIONS)
def tests(session):
    tmpdir = session.create_tmp()
    session.install("-r", "requirements-tests.txt")
    session.install("-e", ".")
    tests = session.posargs or ["ncolony"]
    session.run(
        "python",
        "-Wall",
        "-Wignore::DeprecationWarning",
        "-m",
        "coverage",
        "run",
        "--branch",
        "--source=ncolony",
        "--omit=**/__main__.py,**/tests/*.py",
        "-m",
        "twisted.trial",
        *tests,
        env=dict(COVERAGE_FILE=os.path.join(tmpdir, "coverage"), TMPDIR=tmpdir),
    )
    fail_under = "--fail-under=100"
    session.run(
        "coverage",
        "report",
        fail_under,
        "--show-missing",
        "--skip-covered",
        env=dict(COVERAGE_FILE=os.path.join(tmpdir, "coverage")),
    )


@nox.session(python=VERSIONS[-1])
def build(session):
    session.install("build")
    session.run("python", "-m", "build", "--wheel")


@nox.session(python=VERSIONS[-1])
def lint(session):
    files = ["src/", "noxfile.py"]
    session.install("-r", "requirements-lint.txt")
    session.install("-e", ".")
    session.run("black", "--check", "--diff", *files)
    black_compat = ["--max-line-length=88", "--ignore=E203,E503,W503"]
    session.run("flake8", *black_compat, "src/")
    session.run(*"pylint --rcfile admin/pylintrc ncolony".split())


@nox.session(python=VERSIONS[-1])
def mypy(session):
    session.install("-r", "requirements-mypy.txt")
    session.install("-e", ".")
    session.run(
        "mypy",
        "--warn-unused-ignores",
        "--ignore-missing-imports",
        "src/ncolony/",
    )


@nox.session(python=VERSIONS[-1])
def docs(session):
    """Build the documentation."""
    output_dir = os.path.abspath(os.path.join(session.create_tmp(), "output"))
    doctrees, html = map(
        functools.partial(os.path.join, output_dir), ["doctrees", "html"]
    )
    session.run("rm", "-rf", output_dir, external=True)
    session.install("-r", "requirements-docs.txt")
    session.install("-e", ".")
    sphinx = ["sphinx-build", "-b", "html", "-W", "-d", doctrees, ".", html]
    session.cd("doc")
    session.run(*sphinx)


@nox.session(python=VERSIONS[-1])
def refresh_deps(session):
    """Refresh the requirements-*.txt files"""
    session.install("pip-tools")
    for deps in ["tests", "docs", "lint", "mypy"]:
        session.run(
            "pip-compile",
            "--extra",
            deps,
            "pyproject.toml",
            "--output-file",
            f"requirements-{deps}.txt",
        )
