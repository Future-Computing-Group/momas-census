from xfam_full import FIELDS, stage2


def _row(i, agent, owners, interests):
    return {"id": f"x{i:05d}", "agent": agent, "owners_derived": owners, "interests": interests, "llm_basis": "na", "faces_other_parties": "no",
            "faces_quote": "", "one_party_runs_all": "yes", "eval_run": "one", "focus_derived": "agent"}


def test_stage2_parts_are_disjoint_complete_and_deterministic():
    rows = ([_row(i, "yes", "several", "several-conflicting") for i in range(5)] + [_row(i, "no", "several", "several-aligned") for i in range(5, 8)]
            + [_row(i, "yes", "several", "adversarial") for i in range(8, 10)] + [_row(i, "yes", "one", "one") for i in range(10, 400)]
            + [_row(i, "no", "one", "one") for i in range(400, 900)])
    items = {r["id"]: {"xid": r["id"], "sample_id": None, "venue": "icml-2025", "main_track": True, "title": "t", "abstract": "a"} for r in rows}
    out = stage2(rows, items, seed=5)
    parts = {p: [x for x in out if x["part"] == p] for p in "abcd"}
    assert [len(parts[p]) for p in "abcd"] == [5, 3, 300, 200]
    assert len({x["xid"] for x in out}) == len(out)
    assert all(x["agent"] == "yes" and x["owners_derived"] == "one" for x in parts["c"])
    assert all(x["agent"] == "no" and x["owners_derived"] == "one" for x in parts["d"])
    assert set(out[0]) == {"part", "xid", "sample_id", "venue", "main_track", "title", "abstract", *FIELDS}
    assert stage2(rows, items, seed=5) == out


def _ext_rows():
    rows, n = [], 0
    for venue, k_sev, k_llm, k_agent, k_other in (("iclr-2025", 40, 200, 400, 1000), ("aamas-2025", 30, 10, 80, 40)):
        for kind, k in (("sev", k_sev), ("llm", k_llm), ("agent", k_agent), ("other", k_other)):
            for j in range(k):
                n += 1
                r = _row(n, "no" if kind == "other" else "yes", "several" if kind == "sev" else ("na" if kind == "other" and j % 10 == 0 else "one"),
                         ("several-conflicting", "adversarial", "one")[j % 3] if kind == "sev" else "one")
                r["llm_basis"] = "yes" if kind == "llm" else "no"
                rows.append((venue, r))
    items = {r["id"]: {"xid": r["id"], "sample_id": None, "venue": v, "main_track": True, "title": f"t{r['id']}", "abstract": "a"} for v, r in rows}
    return [r for _, r in rows], items


def test_stage2_ext_confirms_every_owners_several_paper_and_slices_negatives_per_venue_and_llm_basis():
    from xfam_full import QUOTA, stage2_ext
    rows, items = _ext_rows()
    out = stage2_ext(rows, items, seed=5)
    assert len({x["xid"] for x in out}) == len(out)
    sev = {r["id"] for r in rows if r["owners_derived"] == "several"}
    assert {x["xid"] for x in out if x["part"] in "abe"} == sev  # every owners-several paper, whatever its interests
    assert all(x["owners_derived"] != "several" for x in out if x["part"] in "cd")
    n = lambda p, v, llm=None: sum(x["part"] == p and x["venue"] == v and (llm is None or (x["llm_basis"] == "yes") == llm) for x in out)
    assert (n("c", "iclr-2025", True), n("c", "iclr-2025", False), n("d", "iclr-2025")) == (QUOTA["agent-llm"], QUOTA["agent"], QUOTA["other"])
    assert (n("c", "aamas-2025", True), n("c", "aamas-2025", False), n("d", "aamas-2025")) == (10, 80, 40)  # small strata are taken whole
    assert n("d", "iclr-2025") == 300 and any(x["owners_derived"] == "na" for x in out if x["part"] == "d")  # owners na are negatives too
    assert set(out[0]) == {"part", "xid", "sample_id", "venue", "main_track", "title", "abstract", *FIELDS}
    assert stage2_ext(rows, items, seed=5) == out and stage2_ext(list(reversed(rows)), items, seed=5) == out


def test_confirm_batches_are_blind_shuffled_complete_and_keyed_by_xid():
    from xfam_full import confirm_batches, confirm_brief
    rows, items = _ext_rows()
    from xfam_full import stage2_ext
    s2 = stage2_ext(rows, items, seed=5)
    b = confirm_batches(s2, seed=3)
    assert all(len(x) <= 70 for x in b) and sorted(i["id"] for x in b for i in x) == sorted(x["xid"] for x in s2)
    assert all(set(i) == {"id", "title", "abstract"} for x in b for i in x)
    assert [i["id"] for i in b[0]] != [x["xid"] for x in s2][:len(b[0])]  # shuffled, not in part order
    assert confirm_batches(s2, seed=3) == b
    t = confirm_brief("ext-confirm-03")
    assert "BASE/codebook-v3.md" in t and "BASE/data/batches/ext-confirm-03.json" in t and "BASE/data/coded/ext-confirm-03.jsonl" in t
    assert "iclr" not in t.lower() and "aamas" not in t.lower()


def test_main_ext_runs_end_to_end_on_a_synthetic_stage1_output(tmp_path, monkeypatch):
    import json

    import pytest
    from xfam_full import main_ext
    rows, items = _ext_rows()
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data" / "xfam").mkdir(parents=True)
    (tmp_path / "data" / "batches").mkdir()
    (tmp_path / "data/xfam/items-ext.jsonl").write_text("".join(json.dumps(items[r["id"]]) + "\n" for r in rows))
    (tmp_path / "parsed.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows[:-1]))
    with pytest.raises(AssertionError):
        main_ext("parsed.jsonl")  # one item missing from stage 1
    (tmp_path / "parsed.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    main_ext("parsed.jsonl")
    s2 = json.load(open("data/xfam/stage2-ext.json"))
    briefs = [json.loads(l) for l in open("data/batches/ext-confirm-briefs.jsonl")]
    got = [i["id"] for b in briefs for i in json.load(open(f"data/batches/{b['batch']}.json"))]
    assert sorted(got) == sorted(x["xid"] for x in s2) and sum(b["n"] for b in briefs) == len(s2)


def test_stage2_ext_confirms_a_small_venue_in_full_as_ec_was():
    from xfam_full import stage2_ext
    rows, items = _ext_rows()
    out = stage2_ext(rows, items, seed=5, quota={"agent-llm": 5, "agent": 5, "other": 5})
    assert sum(x["venue"] == "aamas-2025" for x in out) == sum(v["venue"] == "aamas-2025" for v in items.values())  # 160 papers <= FULL_VENUE
    assert sum(x["venue"] == "iclr-2025" and x["part"] in "cd" for x in out) == 15


def test_ext_brief_is_the_dispatched_confirm_brief():
    import json, xfam_full
    used = [json.loads(l) for l in open("coding/briefs.jsonl") if '"confirm-e00.jsonl"' in l][0]["brief"]
    assert xfam_full.confirm_brief("confirm-e00") == used


def test_ea_sensitivity_gets_its_own_stage2_file_batches_and_private_dirs(tmp_path, monkeypatch):
    import json
    from xfam_full import confirm_brief, main_ext
    rows, items = _ext_rows()
    ea = [r for r in rows if items[r["id"]]["venue"] == "aamas-2025"]
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data" / "xfam").mkdir(parents=True)
    (tmp_path / "data" / "batches").mkdir()
    (tmp_path / "data/xfam/items-ext-ea.jsonl").write_text("".join(json.dumps({**items[r["id"]], "venue": "aamas-2025-ea"}) + "\n" for r in ea))
    (tmp_path / "parsed.jsonl").write_text("".join(json.dumps(r) + "\n" for r in ea))
    main_ext("parsed.jsonl", tag="ext-ea")
    s2 = json.load(open("data/xfam/stage2-ext-ea.json"))
    assert len(s2) == len(ea)  # a venue under FULL_VENUE is confirmed in full
    briefs = [json.loads(l) for l in open("data/batches/ext-ea-confirm-briefs.jsonl")]
    assert briefs[0]["batch"] == "ext-ea-confirm-00" and "BASE/data/coded/ext-ea-confirm-00.jsonl" in briefs[0]["brief"]
    assert not (tmp_path / "data/xfam/stage2-ext.json").exists()
    # parallel coders never share a private directory
    assert "/private/tmp/conf-ext-ea-00/" in confirm_brief("ext-ea-confirm-00") and "/private/tmp/conf-ext-00/" in confirm_brief("ext-confirm-00")


def test_agreement_batch_is_a_seeded_blind_slice_of_one_venue_outside_the_confirm_glob():
    from xfam_full import agreement_batch, confirm_brief
    s2 = [{"xid": f"y{n:03d}", "venue": "aamas-2025" if n % 2 else "iclr-2025", "title": f"T{n}", "abstract": f"A{n}"} for n in range(300)]
    name, b = agreement_batch(s2, "aamas-2025", n=70, seed=81)
    assert name == "ext-dup-aamas" and len(b) == 70 and all(set(x) == {"id", "title", "abstract"} for x in b)
    assert {x["id"] for x in b} <= {x["xid"] for x in s2 if x["venue"] == "aamas-2025"} and agreement_batch(s2, "aamas-2025", n=70, seed=81)[1] == b
    assert "BASE/data/coded/ext-dup-aamas.jsonl" in confirm_brief(name) and "confirm-" not in name  # never read as a primary code
