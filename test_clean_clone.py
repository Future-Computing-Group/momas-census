"""Runs test_clean_clone.sh: a clone of the committed HEAD regenerates si/, docs/fragments/ and Fig. 2 byte for byte."""
import subprocess

import pytest


@pytest.mark.skipif(subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True).returncode != 0, reason="needs a git checkout")
def test_clean_clone_regenerates_the_committed_outputs():
    r = subprocess.run(["sh", "test_clean_clone.sh"], capture_output=True, text=True)
    assert r.returncode == 0, (r.stdout + r.stderr)[-3000:]
