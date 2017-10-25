import os
from io import StringIO

import sh


def test_generated_command_exists():
    out = StringIO()
    sh.command('-v', 'tor-archivist', _out=out)
    out.seek(0)
    cmd = out.read().strip()
    assert os.path.basename(cmd) == 'tor-archivist'
