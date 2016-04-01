# Module to allow easy switching between using an official published release
# and a local testing version.

Testing = True

from pkg_resources import require
if Testing:
    import sys
    import os
    sys.path.append(os.path.abspath(os.path.join(
        os.path.dirname(__file__), '..')))
    require('numpy')
else:
    require('cothread')
