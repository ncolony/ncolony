# Copyright (c) Moshe Zadka
# See LICENSE for details.
"""Helper functions"""
import json

def dumps2utf8(something):
    return json.dumps(something).encode('utf-8')
