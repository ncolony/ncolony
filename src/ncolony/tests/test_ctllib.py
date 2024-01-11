# Copyright (c) Moshe Zadka
# See LICENSE for details.

"""Tests for ncolony.ctllib"""

import argparse
import io
import json
import os
import shutil
import unittest

from ncolony import ctllib


def jsonFrom(fname):
    """Load JSON from a file"""
    with io.open(fname, "r", encoding="utf-8") as fp:
        return json.loads(fp.read())


class TestArgParsing(unittest.TestCase):

    """Test the argument parser"""

    def setUp(self):
        """Initialize the parser, required arguments"""
        self.parser = ctllib.PARSER
        self.base = ["--messages", "messages", "--config", "config"]

    def test_required_messages(self):
        """Make sure it fails if --messages is missing"""
        with self.assertRaises(SystemExit):
            self.parser.parse_args(["--config", "config", "restart-all"])

    def test_required_config(self):
        """Make sure it fails if --config is missing"""
        with self.assertRaises(SystemExit):
            self.parser.parse_args(["--messages", "messages", "restart-all"])

    def test_restart_all(self):
        """Check restart-all subcommand parsing"""
        res = self.parser.parse_args(self.base + ["restart-all"])
        self.assertEqual(res.messages, "messages")
        self.assertEqual(res.config, "config")
        self.assertIs(res.func, ctllib.restartAll)

    def test_restart(self):
        """Check restart subcommand parsing"""
        res = self.parser.parse_args(self.base + ["restart", "hello"])
        self.assertEqual(res.name, "hello")
        self.assertIs(res.func, ctllib.restart)

    def test_add_needs_cmd(self):
        """Check add subcommand fails without required --cmd"""
        with self.assertRaises(SystemExit):
            self.parser.parse_args(self.base + ["add", "hello"])

    def test_add(self):
        """Check add subcommand parsing"""
        res = self.parser.parse_args(self.base + ["add", "hello", "--cmd", "/bin/echo"])
        self.assertEqual(res.name, "hello")
        self.assertEqual(res.cmd, "/bin/echo")
        self.assertIs(res.func, ctllib.add)

    def test_add_full(self):
        """Add subcommand parsing when all optional arguments are given"""
        extras = {
            "ncolony.beatcheck": {"period": 10, "grace": 3, "status": "foo.status"}
        }
        extrasJSON = json.dumps(extras)
        with open("extras.json", "w") as fp:
            fp.write(extrasJSON)
        args = self.base + [
            "add",
            "hello",
            "--cmd",
            "/bin/echo",
            "--arg",
            "hello",
            "--arg",
            "world",
            "--env",
            "world=616",
            "--env",
            "status=good",
            "--uid",
            "5",
            "--gid",
            "6",
            "--extra",
            "extras.json",
            "--env-inherit",
            "PATH",
            "--env-inherit",
            "PYTHONPATH",
        ]
        res = self.parser.parse_args(args)
        self.assertEqual(res.name, "hello")
        self.assertEqual(res.cmd, "/bin/echo")
        self.assertEqual(res.args, ["hello", "world"])
        self.assertEqual(res.env, ["world=616", "status=good"])
        self.assertEqual(res.env_inherit, ["PATH", "PYTHONPATH"])
        self.assertEqual(res.uid, 5)
        self.assertEqual(res.gid, 6)
        self.assertEqual(res.extras, extras)
        self.assertIs(res.func, ctllib.add)

    def test_remove(self):
        """Check remove subcommand parsing"""
        res = self.parser.parse_args(self.base + ["remove", "hello"])
        self.assertEqual(res.name, "hello")
        self.assertIs(res.func, ctllib.remove)

    def test_call(self):
        """Check the 'call' function"""
        ns = argparse.Namespace()
        results = []

        def _func(places, **kwargs):
            results.append((places, kwargs))

        ns.func = _func
        ns.config = "config1"
        ns.messages = "messages1"
        ns.foo = "bar"
        ns.baz = "quux"
        ctllib.call(ns)
        self.assertEqual(
            results,
            [
                (
                    ctllib.Places(config="config1", messages="messages1"),
                    dict(foo="bar", baz="quux"),
                )
            ],
        )


class TestController(unittest.TestCase):

    """Check the control functions"""

    def setUp(self):
        """Set up configuration and build/cleanup directories"""
        self.places = ctllib.Places(config="config", messages="messages")

        def _cleanup():
            for d in self.places:
                if os.path.exists(d):
                    shutil.rmtree(d)

        _cleanup()
        self.addCleanup(_cleanup)
        for d in self.places:
            os.mkdir(d)

    def test_main(self):
        """Test that control via the main() function works"""
        argv = [
            "ctl",
            "--messages",
            self.places.messages,
            "--config",
            self.places.config,
            "restart-all",
        ]
        ctllib.main(argv)
        (fname,) = os.listdir(self.places.messages)
        fname = os.path.join(self.places.messages, fname)
        d = jsonFrom(fname)
        self.assertEqual(d, dict(type="RESTART-ALL"))

    def test_main_no_ctl(self):
        """Test that control via the main() function works"""
        argv = [
            "--messages",
            self.places.messages,
            "--config",
            self.places.config,
            "restart-all",
        ]
        ctllib.main(argv)
        (fname,) = os.listdir(self.places.messages)
        fname = os.path.join(self.places.messages, fname)
        d = jsonFrom(fname)
        self.assertEqual(d, dict(type="RESTART-ALL"))

    def test_add_and_remove(self):
        """Test that add/remove work"""
        ctllib.add(self.places, "hello", cmd="/bin/echo", args=["hello"])
        fname = os.path.join(self.places.config, "hello")
        d = jsonFrom(fname)
        self.assertEqual(d, dict(args=["/bin/echo", "hello"]))
        ctllib.remove(self.places, "hello")
        self.assertFalse(os.path.exists(fname))

    def test_add_with_env_and_extras(self):
        """Test that add with optional environment works"""
        extras = dict(goodbye=[1, 2, 3])
        ctllib.add(
            self.places,
            "hello",
            cmd="/bin/echo",
            args=["hello"],
            env=["world=616"],
            extras=extras,
        )
        fname = os.path.join(self.places.config, "hello")
        d = jsonFrom(fname)
        self.assertEqual(
            d,
            dict(env={"world": "616"}, goodbye=[1, 2, 3], args=["/bin/echo", "hello"]),
        )

    def test_add_with_uid(self):
        """Test that add with optional uid works"""
        ctllib.add(self.places, "hello", cmd="/bin/echo", args=["hello"], uid=1024)
        fname = os.path.join(self.places.config, "hello")
        d = jsonFrom(fname)
        self.assertEqual(d, dict(uid=1024, args=["/bin/echo", "hello"]))

    def test_add_with_gid(self):
        """Test that add with optional gid works"""
        ctllib.add(self.places, "hello", cmd="/bin/echo", args=["hello"], gid=1024)
        fname = os.path.join(self.places.config, "hello")
        d = jsonFrom(fname)
        self.assertEqual(d, dict(gid=1024, args=["/bin/echo", "hello"]))

    def test_add_with_env_inherit(self):
        """Test that add with optional gid works"""
        ctllib.add(
            self.places, "hello", cmd="/bin/echo", args=["hello"], env_inherit=["PATH"]
        )
        fname = os.path.join(self.places.config, "hello")
        d = jsonFrom(fname)
        self.assertEqual(d["env_inherit"], ["PATH"])

    def test_restart(self):
        """Test that restart works"""
        ctllib.restart(self.places, "hello")
        (fname,) = os.listdir(self.places.messages)
        fname = os.path.join(self.places.messages, fname)
        d = jsonFrom(fname)
        self.assertEqual(d, dict(type="RESTART", name="hello"))
        ctllib.restart(self.places, "goodbye")
        things = (
            jsonFrom(os.path.join(self.places.messages, fname))
            for fname in os.listdir(self.places.messages)
        )
        names = set()
        for thing in things:
            self.assertEqual(thing.pop("type"), "RESTART")
            [(k, v)] = thing.items()
            self.assertEqual(k, "name")
            names.add(v)
        self.assertEqual(names, set(("hello", "goodbye")))

    def test_restart_all(self):
        """Test that restart-all works"""
        ctllib.restartAll(self.places)
        (fname,) = os.listdir(self.places.messages)
        fname = os.path.join(self.places.messages, fname)
        d = jsonFrom(fname)
        self.assertEqual(d, dict(type="RESTART-ALL"))

    def test_extra_protection(self):
        """Test that messages have the PID in them"""
        ctllib.restartAll(self.places)
        (fname,) = os.listdir(self.places.messages)
        pid = str(os.getpid())
        self.assertIn(pid, fname)
