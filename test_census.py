from census import dedupe, flags, sample


def test_dedupe_keeps_one_entry_per_title():
    rows = [{"name": "A Paper", "abstract": "x"}, {"name": "a paper!", "abstract": "x"}, {"name": "B", "abstract": "y"}]
    assert [r["name"] for r in dedupe(rows)] == ["A Paper", "B"]


def test_agent_flag_hits_agent_terms_and_misses_unrelated_uses():
    assert flags("LLM agents use tools to browse the web")["agent"]
    assert flags("An agentic framework for coding")["agent"]
    assert flags("We study multi-agent reinforcement learning")["agent"]
    # chemistry "agent" and "reagent" are not autonomous agents
    assert not flags("a reducing agent and a reagent in synthesis")["agent"]
    assert not flags("Image classification with transformers")["agent"]


def test_multiparty_flag():
    assert flags("A mechanism design approach with strategic agents")["multiparty"]
    assert flags("Federated learning across hospitals")["multiparty"]
    assert flags("Equilibria in general-sum games")["multiparty"]
    assert not flags("Faster attention kernels")["multiparty"]


def test_sample_is_deterministic_and_seed_dependent():
    rows = [{"name": str(i)} for i in range(100)]
    a, b, c = sample(rows, 10, seed=1), sample(rows, 10, seed=1), sample(rows, 10, seed=2)
    assert a == b and a != c and len(a) == 10
    assert len(sample(rows[:5], 10, seed=1)) == 5


def test_kappa_perfect_chance_and_known_value():
    from census import kappa
    assert kappa(["a", "b", "a"], ["a", "b", "a"]) == 1.0
    # observed 0.5, expected 0.5 -> 0
    assert abs(kappa(["a", "a", "b", "b"], ["a", "b", "a", "b"])) < 1e-12
    # 2x2 table [[20,5],[10,15]]: po=0.7, pe=0.5 -> 0.4
    a = ["y"] * 25 + ["n"] * 25
    b = ["y"] * 20 + ["n"] * 5 + ["y"] * 10 + ["n"] * 15
    assert abs(kappa(a, b) - 0.4) < 1e-12


def test_llm_agent_flag():
    from census import flags
    assert flags("We build LLM agents for web navigation")["llm_agent"]
    assert flags("An agentic coding system")["llm_agent"]
    assert not flags("A deep RL agent for Atari")["llm_agent"]


def test_build_sample_strata_unique_ids_and_overlap():
    from build_sample import build
    venues = {
        "v-2025": [{"name": f"p{i}", "abstract": ("LLM agents" if i % 10 == 0 else "an RL agent" if i % 5 == 0 else "x")} for i in range(200)],
        "ec-2025": [{"name": f"e{i}", "abstract": "auctions"} for i in range(30)],
    }
    items, overlap = build(venues, n_random=50, n_agent=10, seed=7, overlap_frac=0.2)
    ids = [x["id"] for x in items]
    assert len(ids) == len(set(ids))
    v = [x for x in items if x["venue"] == "v-2025"]
    assert sum("random" in x["strata"] for x in v) == 50
    assert sum("llm_agent" in x["strata"] for x in v) == 20  # all LLM-agent papers in 2025 cells
    assert sum("agent" in x["strata"] for x in v) == 10
    assert sum(x["venue"] == "ec-2025" for x in items) == 30  # control corpus coded in full
    assert set(overlap) <= set(ids) and len(overlap) == round(0.2 * len(ids))
    assert build(venues, n_random=50, n_agent=10, seed=7, overlap_frac=0.2) == (items, overlap)


def test_validate_flags_missing_ids_bad_values_and_accepts_good():
    from census import validate
    good = {"id": "a", "agent": "yes", "data": "pooled", "objective": "single", "control": "central", "interests": "one", "owners": "one", "boundary": "no", "confidence": "high", "note": "x"}
    assert validate([good], ["a"]) == []
    bad = dict(good, owners="many")
    assert any("owners" in e for e in validate([bad], ["a"]))
    assert any("missing" in e for e in validate([good], ["a", "b"]))
    assert any("unexpected" in e for e in validate([good, dict(good, id="z")], ["a"]))


def test_build_sample_ids_are_opaque():
    from build_sample import build
    venues = {"ec-2025": [{"name": "e1", "abstract": "a"}], "neurips-2025": [{"name": "p1", "abstract": "LLM agents"}]}
    items, _ = build(venues, n_random=5, n_agent=5, seed=1, overlap_frac=0.0)
    for x in items:
        assert "ec" not in x["id"] and "2025" not in x["id"] and "neurips" not in x["id"]


def test_read_to_end_matches_last_words_modulo_punctuation_and_case():
    from census import read_to_end
    abstract = "We study agents. Code is at https://github.com/x/y. Results hold in Section 5."
    assert read_to_end("results hold in Section 5", abstract)
    assert read_to_end("Results hold in Section 5.", abstract)
    # a coder that stopped early reports words from the middle
    assert not read_to_end("We study agents. Code", abstract)
    assert not read_to_end("", abstract)


def test_kappa_is_undefined_when_both_coders_give_one_value():
    from census import kappa
    assert kappa([0] * 5, [0] * 5) is None
    assert kappa(["a"] * 4, ["b"] * 4) == 0.0  # one value each, but different values: chance agreement 0
