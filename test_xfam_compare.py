from xfam_compare import compare

ITEMS = {"x1": {"sample_id": "q1", "title": "A"}, "x2": {"sample_id": "q2", "title": "B"}, "x3": {"sample_id": None, "title": "C"}}
BASE = {"agent": "yes", "interests": "several-conflicting", "owners": "several", "boundary": "yes"}


def test_compare_maps_via_sample_id_and_lists_owner_disagreements():
    smoke = [{"id": "x1", **BASE, "llm_basis": "yes", "quote": "q-a"}, {"id": "x2", **BASE, "owners": "one", "llm_basis": "no", "quote": "q-b"}, {"id": "x3", **BASE}]
    primary = {"q1": dict(BASE), "q2": {**BASE, "owners": "several"}}
    llm = {"q1": {"llm_basis": "yes"}}
    rows, owners = compare(smoke, ITEMS, primary, llm)
    assert rows["owners"][:2] == (2, 1)
    assert rows["agent"][:2] == (2, 2)
    # category: q1 multi-principal both; q2 coder multi-principal, model single
    assert rows["category"][:2] == (2, 1)
    assert rows["llm_basis"][:2] == (1, 1)  # only where an LLM_BASIS code exists
    assert owners == [{"sample_id": "q2", "title": "B", "claude": "several", "model": "one", "interests": "several-conflicting", "quote": "q-b"}]


def test_focus_check_takes_every_several_up_to_12_then_random():
    from xfam_compare import focus_check
    items = {f"x{i}": {"sample_id": f"q{i}", "title": f"T{i}", "abstract": f"A{i}"} for i in range(40)}
    smoke = [{"id": f"x{i}", "owners": "several" if i < 5 else "one", "focus": "agent", "interests": "one", "eval_run": "one", "quote": ""} for i in range(40)]
    out = focus_check(smoke, items, seed=1)
    assert len(out) == 20 and len({o["id"] for o in out}) == 20
    assert {f"q{i}" for i in range(5)} <= {o["id"] for o in out}
    assert set(out[0]) == {"id", "title", "abstract", "focus", "owners", "interests", "eval_run", "quote"}
    assert focus_check(smoke, items, seed=1) == out
    many = [dict(r, owners="several") for r in smoke]
    assert len(focus_check(many, items, seed=1)) == 20  # 12 several, then 8 random others (also several here)


def test_recode_check_keeps_membership_and_order():
    from xfam_compare import recode_check
    items = {f"x{i}": {"sample_id": f"q{i}", "title": f"T{i}", "abstract": f"A{i}"} for i in range(5)}
    prev = [{"id": "q3"}, {"id": "q1"}]
    smoke = [{"id": f"x{i}", "owners": "one", "focus": "interaction", "interests": "one", "eval_run": "one", "quote": str(i)} for i in range(5)]
    out = recode_check(prev, smoke, items)
    assert [o["id"] for o in out] == ["q3", "q1"] and out[0]["quote"] == "3" and out[1]["abstract"] == "A1"
