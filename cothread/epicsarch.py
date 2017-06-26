
__all__ = [
    'epics_host_arch',
]

# Mapping from host architecture to EPICS host architecture name can be done
# with a little careful guesswork.  As EPICS architecture names are a little
# arbitrary this isn't guaranteed to work.
_epics_system_map = {
    ('Linux',   '32bit'):   'linux-x86',
    ('Linux',   '64bit'):   'linux-x86_64',
    ('Darwin',  '32bit'):   'darwin-x86',
    ('Darwin',  '64bit'):   'darwin-x86',
    ('Windows', '32bit'):   'win32-x86',
    ('Windows', '64bit'):   'windows-x64',  # Not quite yet!
}

def _get_arch():
    import os
    try:
        return os.environ['EPICS_HOST_ARCH']
    except KeyError:
        import platform
        system = platform.system()
        bits = platform.architecture()[0]
        return _epics_system_map[(system, bits)]

epics_host_arch = _get_arch()
