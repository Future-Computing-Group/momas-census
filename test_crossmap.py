"""The needs coding: the Box 2 sub-questions, the blind NEEDS coding inputs, the load-time validation of the coded matrix and the need-set crossmap."""
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent
sys.path.append(str(ROOT / "fields" / "run4-broad"))
import crossmap as cm  # noqa: E402
import needs_inputs as ni  # noqa: E402

SUBQ = [{"id": "Q1", "tag": "Rules", "text": "first?"}, {"id": "Q2", "tag": "Rules", "text": "second?"},
        {"id": "Q3", "tag": "Detection", "text": "third & 5%?"}]
ABS = [{"openalex": f"W{c}{i}", "cluster": c, "group": "base" if i < 2 else "run4", "title": f"t{c}{i}", "year": 2000 + i,
        "abstract": None if i == 0 else f"abstract {c}{i}"} for c in ("C1", "C7", "R1") for i in range(3)]


def _inputs(tmp_path):
    batches, keys = ni.build(ABS, SUBQ)
    return batches, keys


def _rows(batch, yes):
    """A complete, valid coder file: yes for the (q, code) cells in `yes`, citing the literature's lowest-id seed (a base seed)."""
    out = []
    for q in batch["subquestions"]:
        for lit in batch["literatures"]:
            y = (q["id"], lit["code"]) in yes
            out.append({"q": q["id"], "lit": lit["code"], "need": "yes" if y else "no", "seeds": [min(x["id"] for x in lit["seeds"])] if y else [],
                        "result": "a bound" if y else "", "basis": "abstract" if y else ""})
    return out


def _code(keys, coder, cluster):
    return next(k for k, v in keys[coder].items() if v == cluster)


def _write(p, rows):
    p.write_text("".join(json.dumps(r) + "\n" for r in rows))
    return p


# --- the sub-question file ---------------------------------------------------------------------------------------------

def test_subquestion_file_is_the_approved_list():
    sq = json.load(open(ROOT / "data/fields/subquestions.json"))
    assert len(sq) == 25 and len({q["id"] for q in sq}) == 25
    assert all(set(q) == {"id", "tag", "text"} for q in sq)
    assert Counter(q["tag"] for q in sq) == {"Rules": 6, "Detection": 6, "Repair": 4, "Change": 4, "Neutrality": 5}
    assert all(" | " not in q["text"] and q["text"].endswith("?") for q in sq)  # the crossmap line format splits on " | "


# --- inputs: abstracts, blinding, shuffling ----------------------------------------------------------------------------

def test_abstract_from_inverted_index():
    assert ni.abstract({"b": [1], "a": [0, 2]}) == "a b a"
    assert ni.abstract(None) is None and ni.abstract({}) is None


def test_build_blinds_codes_and_shuffles():
    batches, keys = ni.build(ABS, SUBQ)
    assert set(batches) == set(keys) == {"c1", "c2"}
    for c, b in batches.items():
        assert [q["id"] for q in b["subquestions"]] == ["Q1", "Q2", "Q3"]
        assert [l["code"] for l in b["literatures"]] == ["L01", "L02", "L03"]
        assert sorted(keys[c].values()) == ["C1", "C7", "R1"]
        for lit in b["literatures"]:
            src = [a for a in ABS if a["cluster"] == keys[c][lit["code"]]]
            assert sorted(s["id"] for s in lit["seeds"]) == sorted(a["openalex"] for a in src)
            assert all(set(s) == {"id", "title", "year", "abstract"} for s in lit["seeds"])
        text = json.dumps(b)
        assert not any(k in text for k in ('"cluster"', '"group"', '"label"', '"C1"', '"C7"', '"R1"'))
    assert next(s for l in batches["c1"]["literatures"] for s in l["seeds"] if s["id"] == "WC10")["abstract"] == ni.NO_ABSTRACT
    assert ni.build(ABS, SUBQ) == (batches, keys)  # deterministic


def test_built_inputs_on_disk_match_the_data():
    if not (ROOT / "data/batches/needs-c1.json").exists():
        pytest.skip("NEEDS inputs not built")
    sq = json.load(open(ROOT / "data/fields/subquestions.json"))
    ab = json.load(open(ROOT / "data/fields/seeds-broad-abstracts.json"))
    keys = json.load(open(ROOT / "data/fields/needs-keys.json"))
    assert len(ab) == 131 and {a["cluster"] for a in ab} == set(cm.LITS)
    batches = {c: json.load(open(ROOT / f"data/batches/needs-{c}.json")) for c in ("c1", "c2")}
    assert keys.pop("rng_seeds") == ni.CODERS and (batches, keys) == ni.build(ab, sq)
    assert keys["c1"] != keys["c2"]
    for b in batches.values():
        assert len(b["subquestions"]) == 25 and len(b["literatures"]) == 11 and sum(len(l["seeds"]) for l in b["literatures"]) == 131
    man = json.load(open(ROOT / "data/fields/needs-manifest.json"))
    sha = lambda p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest()
    assert man["subquestions_sha256"] == sha("data/fields/subquestions.json")
    assert man["codebook_sha256"] == sha("codebook-needs.md")
    assert man["abstracts_sha256"] == sha("data/fields/seeds-broad-abstracts.json")
    assert all(man["batches"][f] == sha(f"data/batches/{f}") for f in ("needs-c1.json", "needs-c2.json"))
    assert man["brief_template_sha256"] == hashlib.sha256(ni.BRIEF.encode()).hexdigest()


# --- load-time validation of a coder file ------------------------------------------------------------------------------

def test_load_accepts_a_complete_file(tmp_path):
    batches, _ = _inputs(tmp_path)
    got = cm.load_coded(_write(tmp_path / "c1.jsonl", _rows(batches["c1"], {("Q1", "L01")})), batches["c1"])
    assert len(got) == 9 and got[("Q1", "L01")]["need"] == "yes"


@pytest.mark.parametrize("bad", ["missing", "duplicate", "foreign_seed", "no_result", "need_value", "no_with_seeds", "basis", "four_seeds"])
def test_load_rejects_a_bad_file(tmp_path, bad):
    batches, _ = _inputs(tmp_path)
    b = batches["c1"]
    rows = _rows(b, {("Q1", "L01")})
    yes = rows[0]
    other = b["literatures"][1]["seeds"][0]["id"]
    if bad == "missing":
        rows.pop()
    elif bad == "duplicate":
        rows.append(dict(rows[-1]))
    elif bad == "foreign_seed":
        yes["seeds"] = [other]
    elif bad == "no_result":
        yes["result"] = " "
    elif bad == "need_value":
        rows[1]["need"] = "maybe"
    elif bad == "no_with_seeds":
        rows[1]["seeds"] = [b["literatures"][1]["seeds"][0]["id"]]
    elif bad == "basis":
        yes["basis"] = "field"
    elif bad == "four_seeds":
        yes["seeds"] = [s["id"] for s in b["literatures"][0]["seeds"]] * 2
    with pytest.raises(ValueError):
        cm.load_coded(_write(tmp_path / "c1.jsonl", rows), b)


def test_coded_files_on_disk_validate():
    if not cm.coded():
        pytest.skip("NEEDS coding not yet run")
    for c in ("c1", "c2"):
        got = cm.load_coded(ROOT / f"data/coded/needs-{c}.jsonl", json.load(open(ROOT / f"data/batches/needs-{c}.json")))
        assert len(got) == 275


# --- need rules ---------------------------------------------------------------------------------------------------------

def test_both_either_and_the_base_restriction(tmp_path):
    batches, keys = _inputs(tmp_path)
    k1, k2 = (lambda cl: _code(keys, "c1", cl)), (lambda cl: _code(keys, "c2", cl))
    r1 = _rows(batches["c1"], {("Q1", k1("C1")), ("Q1", k1("R1")), ("Q2", k1("C7"))})
    r2 = _rows(batches["c2"], {("Q1", k2("C1")), ("Q2", k2("R1"))})
    coded = {"c1": cm.load_coded(_write(tmp_path / "1.jsonl", r1), batches["c1"]), "c2": cm.load_coded(_write(tmp_path / "2.jsonl", r2), batches["c2"])}
    qs = [q["id"] for q in SUBQ]
    assert cm.needs(coded, keys, qs, "both") == {"Q1": {"C1"}, "Q2": set(), "Q3": set()}
    assert cm.needs(coded, keys, qs, "either") == {"Q1": {"C1", "R1"}, "Q2": {"C7", "R1"}, "Q3": set()}
    # a yes counts on the earlier sample only if a recorded seed is a base seed
    run4 = {a["openalex"] for a in ABS if a["group"] == "run4"}
    for c, rows in (("c1", r1), ("c2", r2)):
        for r in rows:
            if r["q"] == "Q1" and keys[c][r["lit"]] == "C1":
                r["seeds"] = [s for s in run4 if s.startswith("WC1")][:1]
    coded = {"c1": cm.load_coded(_write(tmp_path / "1.jsonl", r1), batches["c1"]), "c2": cm.load_coded(_write(tmp_path / "2.jsonl", r2), batches["c2"])}
    base = {a["openalex"] for a in ABS if a["group"] == "base"}
    assert cm.needs(coded, keys, qs, "both", base)["Q1"] == set()
    assert cm.needs(coded, keys, qs, "either", base)["Q1"] == {"R1"}
    assert cm.needs(coded, keys, qs, "either")["Q1"] == {"C1", "R1"}


def test_kappa_and_yes_rates(tmp_path):
    batches, keys = _inputs(tmp_path)
    r1 = _rows(batches["c1"], {("Q1", _code(keys, "c1", "C1"))})
    r2 = _rows(batches["c2"], {("Q1", _code(keys, "c2", "C1"))})
    coded = {"c1": cm.load_coded(_write(tmp_path / "1.jsonl", r1), batches["c1"]), "c2": cm.load_coded(_write(tmp_path / "2.jsonl", r2), batches["c2"])}
    ag = cm.agreement(coded, keys, SUBQ)
    assert ag["n"] == 9 and ag["kappa"] == 1.0 and ag["yes"] == {"c1": 1, "c2": 1} and ag["by_tag"]["Rules"] == 1.0


# --- links, silent pairs, variants ---------------------------------------------------------------------------------------

M1 = {"2": {"work": {"C1": {"C1": 1, "C7": 0.001, "R1": 0.03}, "C7": {"C1": 0.002, "C7": 1, "R1": 0.004}, "R1": {"C1": 0.01, "C7": 0.001, "R1": 1}},
            "ref": {"C1": {"C1": 0.5, "C7": 0.001, "R1": 0.05}, "C7": {"C1": 0.001, "C7": 0.5, "R1": 0.001}, "R1": {"C1": 0.05, "C7": 0.001, "R1": 0.5}}}}


def test_silent_pairs_one_literature_and_count():
    need = {"Q1": {"C1", "C7"}, "Q2": {"C1"}, "Q3": {"C1", "R1"}}
    r = cm.run(SUBQ, need, M1, "2", 0.005, "work")
    assert r["silent"] == {"Q1": [("C1", "C7", 0.002)]}  # Q2 has one literature, so no pair; C1-R1 is linked
    assert r["n"] == 3 and r["all_linked"] is False
    assert r["lines"][0].startswith("Q1 | first? | needs C1 C7 | silent pairs: C1-C7 (0.002)")
    assert "1 of 3 sub-questions" in r["lines"][-2]
    assert cm.run(SUBQ, need, M1, "2", 0.001, "work")["all_linked"] is True
    assert cm.run(SUBQ, need, M1, "2", 0.005, "rel")["silent"] == {"Q1": [("C1", "C7", 0.002)]}


def test_variants_are_the_sixteen():
    v = cm.VARIANTS
    assert len(v) == 16 and len({cm.stem(*x) for x in v}) == 16 and cm.stem("work", "1", 0.005) == "work_1_0.005"


def _summary(sets_both, sets_either, all_linked=()):
    mk = lambda sets: {s: {"silent": sets[s], "all_linked": s in all_linked} for s in sets}
    return {"broad": {"both": mk(sets_both), "either": mk(sets_either)}, "earlier": {"both": mk(sets_both), "either": mk(sets_either)}}


def test_fragments_exclusion_robust_set_and_table():
    p = [("C1", "C7", 0.001)]
    both = {"work_1_0.005": {}, "rel_2_0.01": {"Q1": p, "Q3": p}, "rel_2_0.02": {"Q1": p}}
    either = {"work_1_0.005": {}, "rel_2_0.01": {"Q1": p, "Q2": p}, "rel_2_0.02": {"Q1": p, "Q2": p}}
    need = {"both": {"Q1": {"C1", "C7"}, "Q2": set(), "Q3": {"C1", "C7"}}, "either": {"Q1": {"C1", "C7", "R1"}, "Q2": {"C1", "C7"}, "Q3": {"C1", "C7"}}}
    ag = {"n": 9, "kappa": 0.5, "yes": {"c1": 2, "c2": 3}, "by_tag": {"Rules": 0.4, "Detection": 1.0}}
    f = cm.fragments(_summary(both, either, {"work_1_0.005"}), SUBQ, need, ag, 0.0123)
    assert f["n3-excluded.tex"] == "the share-of-works measure on the one-seed samples at 0.5\\%" and f["n3-nretained.tex"] == "2"
    assert f["n3-robust.tex"] == "1" and f["n3-robust-ids.tex"] == "Q1" and f["n3-robust-either.tex"] == "2"
    assert f["n3-questions.tex"].startswith("between 1 and 2 ")
    assert f["n3-nsub.tex"] == "3" and f["n3-kappa.tex"] == "0.50"
    assert "0.0123" in f["n3-earlier.tex"]
    rows = f["tab-subquestions.tex"].splitlines()
    assert rows[0] == "\\multicolumn{4}{l}{\\emph{Rules}} \\\\"
    assert rows[1] == "Q1 & first? & C1, C7 [R1] & C1--C7 \\\\"
    assert rows[2] == "Q2 & second? & -- [C1, C7] & -- \\\\"
    assert rows[3].startswith("\\multicolumn{4}{l}{\\emph{Detection}}")
    assert rows[4] == "Q3 & third \\& 5\\%? & C1, C7 & -- \\\\"  # silent in one retained variant only


def test_fragments_without_exclusion():
    p = [("C1", "C7", 0.001)]
    s = {"rel_2_0.01": {"Q1": p}, "rel_2_0.02": {"Q1": p}}
    need = {r: {"Q1": {"C1", "C7"}, "Q2": set(), "Q3": set()} for r in ("both", "either")}
    f = cm.fragments(_summary(s, s), SUBQ, need, {"n": 9, "kappa": 1.0, "yes": {"c1": 2, "c2": 2}, "by_tag": {}}, 0.01)
    assert f["n3-excluded.tex"] == "none" and f["n3-nretained.tex"] == "2" and f["n3-robust.tex"] == "1"


def test_main_leaves_outputs_untouched_without_coding(tmp_path, monkeypatch):
    monkeypatch.setattr(cm, "CODED", {c: tmp_path / f"needs-{c}.jsonl" for c in ("c1", "c2")})
    monkeypatch.setattr(cm, "OUT", tmp_path / "crossmap")
    assert cm.coded() is False
    assert cm.main() is None
    assert not (tmp_path / "crossmap").exists()


def test_computed_exclusion_reproduces_the_one_set_aside_variant():
    """On the stored run-4 links only the one-seed share-of-works measure at 0.5% finds every pair linked; on run 3 none does."""
    for f, want in (("results_m1-eleven-broad.json", {"work_1_0.005"}), ("results_m1-eleven-dcbroad.json", set())):
        m1 = json.load(open(ROOT / "data/fields" / f))["M1"]
        got = {cm.stem(*v) for v in cm.VARIANTS if cm.run([], {}, m1, v[1], v[2], v[0])["all_linked"]}
        assert got == want


def test_table_prints_sub_questions_in_us_spelling():
    subq = [{"id": "Q1", "tag": "Rules", "text": "Which behavioural rules favour agents that re-optimise or maximise, and what does randomisation do to their behaviour?"}]
    need = {r: {"Q1": set()} for r in ("both", "either")}
    s = {"rel_2_0.01": {}}
    f = cm.fragments(_summary(s, s), subq, need, {"n": 1, "kappa": 1.0, "yes": {"c1": 0, "c2": 0}, "by_tag": {}}, 0.01)
    row = f["tab-subquestions.tex"].splitlines()[1]
    assert "Which behavioral rules favor agents that re-optimize or maximize, and what does randomization do to their behavior?" in row
