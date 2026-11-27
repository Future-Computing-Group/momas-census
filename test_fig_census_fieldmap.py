import os
import re
import subprocess
import sys

import pytest

DATA = all(os.path.exists(p) for p in ("data/fields/results_m1-eleven-broad.json", "data/fields/results.json", "data/estimates-twostage.json"))


@pytest.mark.skipif(not DATA, reason="needs the local field-map and census estimates")
def test_fig2_plots_fairness_before_and_after_from_the_default_inputs(tmp_path):
    r = subprocess.run([sys.executable, "fig_census_fieldmap.py", "data/fields", str(tmp_path / "f")], capture_output=True, text=True,
                       env={**os.environ, "PYTHONPATH": "."})
    assert r.returncode == 0, r.stderr[-1500:]
    txt = subprocess.run(["pdftotext", str(tmp_path / "f.pdf"), "-"], capture_output=True, text=True).stdout
    assert re.search(r"2012\W{0,3}2016", txt) and re.search(r"2019\W{0,3}2023", txt)  # pdftotext may drop the en dash glyph


@pytest.mark.skipif(not DATA, reason="needs the local field-map and census estimates")
def test_fig2_is_byte_reproducible(tmp_path):
    for k in ("a", "b"):
        r = subprocess.run([sys.executable, "fig_census_fieldmap.py", "data/fields", str(tmp_path / k)], capture_output=True, text=True,
                           env={**os.environ, "PYTHONPATH": "."})
        assert r.returncode == 0, r.stderr[-1500:]
    assert (tmp_path / "a.pdf").read_bytes() == (tmp_path / "b.pdf").read_bytes()
    assert (tmp_path / "a.png").read_bytes() == (tmp_path / "b.png").read_bytes()
