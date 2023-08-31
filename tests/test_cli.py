import subprocess
import sys

from cothread import __version__


def test_cli_version():
    cmd = [sys.executable, "-m", "cothread", "--version"]
    assert subprocess.check_output(cmd).decode().strip() == __version__
