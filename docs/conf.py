# Copyright (c) Moshe Zadka
# See LICENSE for details.
import os
import sys

up = os.path.dirname(os.path.dirname(__file__))
sys.path.append(up)

import ncolony as module

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.viewcode',
]
master_doc = 'index'
project = module.__name__
copyright = ', '.join((module.metadata['copyright'], module.metadata['author']))
author = module.metadata['author']
version = module.__version__
release = module.__version__
