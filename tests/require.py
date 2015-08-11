# Simple import of local file.
import sys
import os
sys.path.insert(0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    import numpy
except ImportError:
    from pkg_resources import require
    require('numpy')
