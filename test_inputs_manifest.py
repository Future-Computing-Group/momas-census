"""data/inputs-sha256.txt (sha256sum format) pins every file that si_tables.py, attention.py and fig_census_fieldmap.py read; the
clean-clone test (test_clean_clone.sh) shows that these files suffice. Rebuild after a deliberate input change with
`shasum -a 256 $(cut -c67- data/inputs-sha256.txt) > data/inputs-sha256.txt`."""
import hashlib
import subprocess

MANIFEST = "data/inputs-sha256.txt"


def entries():
    return [(l[:64], l[66:]) for l in open(MANIFEST).read().splitlines()]


def test_every_pinned_input_matches_its_sha256():
    bad = [p for h, p in entries() if hashlib.sha256(open(p, "rb").read()).hexdigest() != h]
    assert not bad, bad


def test_every_pinned_input_is_tracked():
    tracked = set(subprocess.run(["git", "ls-files"], capture_output=True, text=True).stdout.splitlines())
    assert len(entries()) > 300 and not [p for _, p in entries() if p not in tracked]
