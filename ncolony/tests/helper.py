# Copyright (c) Moshe Zadka
# See LICENSE for details.
"""Helper functions"""
import json

def dumps2utf8(something):
    """json.dumps and encode to utf-8"""
    return json.dumps(something).encode('utf-8')
