from analyze import wilson, category


def test_wilson_known_values():
    lo, hi = wilson(0, 20)
    assert lo == 0 and abs(hi - 0.1611) < 1e-3
    lo, hi = wilson(10, 20)
    assert abs(lo - 0.2993) < 1e-3 and abs(hi - 0.7007) < 1e-3


def test_category_separates_adversarial_from_multi_principal():
    base = {"owners": "one", "interests": "one"}
    assert category(base) == "single"
    assert category(dict(owners="several", interests="several-conflicting")) == "multi-principal"
    assert category(dict(owners="several", interests="several-aligned")) == "multi-principal"
    assert category(dict(owners="several", interests="adversarial")) == "adversarial"
    assert category(dict(owners="one", interests="adversarial")) == "single"
    assert category(dict(owners="one", interests="several-conflicting")) == "single"
    assert category(dict(owners="na", interests="na")) == "na"


def test_strict_requires_decentralized_control():
    from analyze import strict
    assert strict(dict(owners="several", interests="several-conflicting", control="decentralized"))
    assert not strict(dict(owners="several", interests="several-aligned", control="central"))  # federated server
    assert not strict(dict(owners="one", interests="one", control="central"))


def test_agreement_by_length_split():
    from analyze import agreement
    p = {"a": {"owners": "one"}, "b": {"owners": "several"}, "c": {"owners": "one"}}
    o = {"a": {"owners": "one"}, "b": {"owners": "one"}, "c": {"owners": "one"}}
    n, agree, _ = agreement(p, o, "owners", ids=["a", "b", "c"])
    assert (n, agree) == (3, 2)
    n, agree, _ = agreement(p, o, "owners", ids=["a"])
    assert (n, agree) == (1, 1)


def test_final_codes_apply_author_adjudication_over_coder_codes(tmp_path):
    import json
    from analyze import final_codes
    p = tmp_path / "primary-00.jsonl"
    p.write_text(json.dumps({"id": "q1", "agent": "yes", "owners": "several"}) + "\n" + json.dumps({"id": "q2", "agent": "no", "owners": "one"}) + "\n")
    adj = tmp_path / "adjudicated.json"
    adj.write_text(json.dumps({"q1": {"agent": "no", "owners": "one"}}))
    out = final_codes(str(tmp_path / "primary-*.jsonl"), str(adj))
    assert out["q1"]["agent"] == "no" and out["q1"]["owners"] == "one"
    assert out["q2"] == {"id": "q2", "agent": "no", "owners": "one"}
