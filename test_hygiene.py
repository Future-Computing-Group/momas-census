"""Public-safety guard: no tracked file may carry cluster accounts, cluster or laptop paths, compute-node names, workspace
paths or note identifiers (PATTERNS, every file), or process narrative and scaffolding (NARRATIVE, every file except the paper-text data under
data/, whose titles and abstracts are published text). The patterns are written
so that this file does not match them. `python3 test_hygiene.py --cached` scans the index (the pre-commit hook in .githooks/);
pytest scans the tracked working-tree files."""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PATTERNS = {
    "cluster project id": r"project_\d{7}",
    "cluster scratch path": r"/s[c]ratch/",
    "home path": r"(?i)/u[s]ers/",
    "compute node name": r"\br[cg]\d{4}\b",
    "decision narrative": r"\bP[I] (rulin[g]|decisio[n])",
    "workspace path": r"Dro[p]box|5 Su[p]port|lesson[s]\.md|Revie[w]/",
    "lesson reference": r"\bL[1-3][0-9]{2}\b",
    "note id": r"\b20\d\d-\d\d-\d\d-\d\d\b",
}
NARRATIVE = {
    "note reference": r"FUSILL[I] note",
    "adjudication label": r"(?i)\brulin[g]",
    "plan label": r"Pla[n] [ABC]\b|(?i:\bpla[n][-_ ]a\d)",
    "review narrative": r"(?i)simulated revie[w]|revie[w] round|revie[w] panel|\bIssu[e] \d+|refere[e]|associate edito[r]|rebutta[l]",
    "scaffolding file": r"(?i)\b00-threshol[d]|pre-stated threshol[d]",
    "manuscript host": r"(?i)overlea[f]",
}
PAPER_TEXT = [":(exclude,glob)data/**/*.json", ":(exclude,glob)data/**/*.jsonl", ":(exclude,glob)data/**/*.csv"]


def hits(cached=False):
    out = []
    for group, spec in ((PATTERNS, ["."]), (NARRATIVE, [".", *PAPER_TEXT])):
        for label, rx in group.items():
            cmd = ["git", "grep", "-I", "-n", "-P", *(["--cached"] if cached else []), "-e", rx, "--", *spec]
            r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
            assert r.returncode in (0, 1), r.stderr
            out += [f"[{label}] {line[:160]}" for line in r.stdout.splitlines()]
    return out


def test_patterns_fire():
    samples = {"cluster project id": "project_" + "1234567", "cluster scratch path": "/" + "scratch/x", "home path": "/" + "Users/x",
               "compute node name": "node=r" + "g1234", "decision narrative": "P" + "I rul" + "ing", "workspace path": "Re" + "view/x",
               "lesson reference": "see L" + "231", "note id": "note 2026-11-09" + "-05", "note reference": "FUSILLI " + "note",
               "adjudication label": "rul" + "ing 5", "plan label": "pla" + "n_a2_agreement", "review narrative": "simulated " + "review",
               "scaffolding file": "00-thresh" + "olds.md", "manuscript host": "Over" + "leaf"}
    for label, s in samples.items():
        assert re.search({**PATTERNS, **NARRATIVE}[label], s), label
    for t in ("review " + "round 2", "review " + "panel", "Issue" + " 11", "refer" + "ee 2", "associate " + "editor", "rebut" + "tal"):
        assert re.search(NARRATIVE["review narrative"], t), t
    assert re.search(NARRATIVE["plan label"], "Pla" + "n A2") and not re.search(NARRATIVE["plan label"], "we plan a new run")


def test_no_internal_identifiers_in_tracked_files():
    found = hits()
    assert not found, "hygiene guard:\n" + "\n".join(found)


if __name__ == "__main__":
    found = hits(cached="--cached" in sys.argv)
    print("\n".join(found) or "hygiene guard OK")
    sys.exit(1 if found else 0)
