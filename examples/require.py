# Module to allow easy switching between using an official published release
# and a local testing version.

Testing = True

if Testing:
    import sys
    import os
    sys.path.append(os.path.abspath(os.path.join(
        os.path.dirname(__file__), '../build/lib.linux-i686-2.4')))
else:
    from pkg_resource import require
    require('cothread')
