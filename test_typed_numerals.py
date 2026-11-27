"""Every number in main.tex and supplementary.tex comes from a generated fragment (\\input{si/...}), unless it is structural
(a section, box, note, figure or table number, a list marker, a version, a model name, an identifier, a date or year) or is
listed below. Needs the manuscript directory in NMI_MANUSCRIPT."""
import os
import re

import pytest

MS = os.environ.get("NMI_MANUSCRIPT", "/nonexistent") + "/"

STRUCTURAL = [
    r"(?<!\\)%.*",  # comments
    r"\\(input|cite[tp]?|ref|eqref|label|url|href|texttt|includegraphics|bibliography\w*|documentclass|usepackage|begin|end|multicolumn|"
    r"renewcommand|newcommand|tabinput|arraystretch)\*?(\[[^\]]*\])?\{[^}]*\}(\{[^}]*\})?",
    r"\{\\textwidth\}\{[^}]*\{[^}]*\}[^}]*\}",  # tabularx column specs
    r"\b(19|20)\d\d(-\d\d-\d\d)?\b",  # years and dates
    r"(Section|Sections|Box|Note|Fig\.|Table|Argument|Arguments|stage|Owner|Coder|coder)(~|\s)\d+[a-z]?",
    r"\\textbf\{(Box )?\d+[.]?",  # numbered table rows and box titles
    r"(version|versions)\s\d+(\.\d+)?", r"(Sonnet|Opus)\s\d+(\.\d+)?", r"Gemma[-\s][\w.-]+(\s31B)?", r"revision [0-9a-f]+",
    r"ORCID: [\d-]+", r"S\d{6,}", r"\(\d\)",  # identifiers, list markers
    r"\b[CR]\d\b",  # literature labels C1..C7, R1..R4
    r"\$n > 3f\$", r"Agent2Agent", r"\d-bit",
    r"-?\d*\.?\d+\s*(pt|em|ex|cm|mm|bp)\b", r"\d*\.?\d+\\(textwidth|linewidth|columnwidth)", r"\*\{\d+\}", r"#\d", r"\[\d\]",  # layout
    r"^\d\.\s",  # numbered rows of the argument table
]

# Numbers kept as typed: cited facts, design constants of the coding and the estimator, claim thresholds.
ALLOW = {
    "main.tex": ["roughly 1,200 agents", "about 700 of them", "conservative 95\\% bounds", "white, below 1\\%", "above 100\\%"],
    "supplementary.tex": [
        "at least 0.80 on", "at least 0.67 on", "fewer than 10 papers", "at least 90\\% on the cell",  # pilot design levels
        "temperature 0", "fewer than 30 papers", "its 95\\% Wilson", "conservative 95\\% bounds", "The 95\\% interval", "(2,000 draws)", "95\\% Wilson interval",
        "below 2\\% but not below 1\\%", "past 1\\%", "margin exceeds 1.", "link of 1\\%", "per 10,000",
        "the 100-paper set",
    ],
}
# Typed numbers whose fragments exist (si/...); listed until the text inputs them.
PENDING = {
    "main.tex": ["codes of 20 papers", "coded 156 vendor"],
    "supplementary.tex": [
        "(3,708 main-conference", "coded 177 papers", "codebook: 137 on", "and 40 drawn", "re-coded the 24 papers", "fresh random 40 (64 papers)",
        "on the fresh 40", "from 0.85 to 1.00; cell agreement 97.5\\%", "of 70 of them, 70 EC papers", "frame is 156", "blind on 20 papers",
        "only 3 ICLR",  # no stored record yet
    ],
}


def typed_numbers(text, allowed):
    out = []
    for n, line in enumerate(text.splitlines(), 1):
        for a in allowed:
            line = line.replace(a, " ")
        for p in STRUCTURAL:
            line = re.sub(p, " ", line)
        out += [(n, m.group(), line[max(0, m.start() - 30):m.end() + 20]) for m in re.finditer(r"\d[\d,.]*\d|\d", line)]
    return out


def test_typed_numbers_finds_a_number_outside_fragments_and_structure():
    t = "In 2025, \\input{si/x.tex}\\unskip{} of 12 papers (Section~2, Box~1, version 3.4; Fig.~2a) cite~\\cite{a1}.\n% 99 in a comment"
    assert [x[1] for x in typed_numbers(t, [])] == ["12"]
    assert typed_numbers(t, ["of 12 papers"]) == []


@pytest.mark.skipif(not os.path.exists(MS + "main.tex"), reason="needs the manuscript")
@pytest.mark.parametrize("name", ["main.tex", "supplementary.tex"])
def test_no_typed_number_outside_fragments(name):
    found = typed_numbers(open(MS + name).read(), ALLOW[name] + PENDING[name])
    assert not found, "\n".join(f"{name}:{n}: {x} | {ctx}" for n, x, ctx in found)
