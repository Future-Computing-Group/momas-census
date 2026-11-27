from si_ext import aamas_fragment, count_rows, counts, ea_fragment, ext_rows

M = lambda k, n, lo=None, hi=None: {"confirmed": k, "share": k / n, "lo": (lo if lo is not None else k) / n, "hi": (hi if hi is not None else k) / n}


def _tw():
    main = {"all-2020": {"n": 2983, "several": M(66, 2983, 60, 90), "interaction": M(30, 2983, 28, 50), "simulated": M(100, 2983, 95, 140)},
            "all-2025": {"n": 8545, "several": M(199, 8545, 165, 307), "interaction": M(111, 8545, 94, 205), "simulated": M(300, 8545, 280, 400)},
            "ec-2025": {"n": 203, "census": True, "several": M(139, 203), "interaction": M(131, 203), "simulated": M(5, 203)}}
    ext = {"all-iclr-2025": {"n": 3708, "several": M(80, 3708, 70, 120), "interaction": M(40, 3708, 35, 70), "simulated": M(150, 3708, 140, 200)},
           "all-aamas-2025": {"n": 260, "census": True, "several": M(120, 260), "interaction": M(90, 260), "simulated": M(40, 260)}}
    return {**main, "ext": ext, "ext-ea": {"all-aamas-2025-ea": {"n": 160, "census": True, "several": M(70, 160), "interaction": M(50, 160), "simulated": M(10, 160)}}}


R2 = {"parties": {"all-2020": {"parties_ai-agents": M(4, 2983, 3, 9)}, "all-2025": {"parties_ai-agents": M(24, 8545, 17, 106)}, "ec-2025": {"parties_ai-agents": M(3, 203)}}}
R2EXT = {"ext": {"parties": {"all-aamas-2025": {"parties_ai-agents": M(25, 260)}, "all-iclr-2025": {"parties_ai-agents": M(9, 3708, 8, 20)}}},
         "ext-ea": {"parties": {"all-aamas-2025-ea": {"parties_ai-agents": M(4, 160)}}}}


def test_ext_rows_bring_aamas_and_hold_iclr_back():
    tw = _tw()
    assert ext_rows(tw) == [("AAMAS 2025", tw["ext"]["all-aamas-2025"])]
    assert ext_rows({k: v for k, v in tw.items() if k != "ext"}) == []


def test_counts_scale_the_bounds_by_n_and_are_direct_for_full_venues():
    c = counts(_tw(), R2, R2EXT)
    assert c["all-2025"]["several"] == {"count": 199, "lo": 165, "hi": 307, "direct": False}
    assert c["all-aamas-2025"]["several"] == {"count": 120, "lo": 120, "hi": 120, "direct": True}
    assert c["all-aamas-2025"]["parties_ai-agents"]["count"] == 25 and c["all-iclr-2025"]["parties_ai-agents"]["hi"] == 20
    assert c["ec-2025"]["n"] == 203 and set(c) == {"all-2020", "all-2025", "all-iclr-2025", "all-aamas-2025", "all-aamas-2025-ea", "ec-2025"}
    assert c["all-aamas-2025-ea"]["several"] == {"count": 70, "lo": 70, "hi": 70, "direct": True}
    assert "parties_ai-agents" not in counts(_tw(), R2, {})["all-aamas-2025"]  # parties codes not in yet


def test_count_rows_carry_iclr_and_the_ea_papers_and_read_numbers_from_the_json():
    rows = count_rows(counts(_tw(), R2, R2EXT))
    assert [r.split(" & ")[0] for r in rows] == ["NeurIPS + ICML 2020", "NeurIPS + ICML 2025", "ICLR 2025", "AAMAS 2025", "AAMAS 2025 EA + Blue Sky", "EC 2025"]
    aamas = [r for r in rows if r.startswith("AAMAS 2025 &")][0]
    assert "260" in aamas and "120" in aamas and "25" in aamas
    assert "80 (70--120)" in [r for r in rows if r.startswith("ICLR 2025")][0]  # two-stage: an interval; AAMAS: a direct count
    assert "199 (165--307)" in [r for r in rows if r.startswith("NeurIPS + ICML 2025")][0]


def test_aamas_and_ea_fragments_carry_n_and_share_from_the_json():
    f = aamas_fragment(_tw(), R2EXT)
    assert "120 of 260" in f and "46.2\\%" in f and "25" in f
    assert "70 of 160" in ea_fragment(_tw()) and "43.8\\%" in ea_fragment(_tw())


def test_write_without_parties_leaves_out_the_count_table_and_the_aamas_fragment(tmp_path):
    from si_ext import write
    write(tmp_path, _tw(), R2, {}, str(tmp_path / "counts.json"), parties=False)
    assert sorted(p.name for p in tmp_path.iterdir()) == ["aamas-ea-short.tex"]
    write(tmp_path, _tw(), R2, R2EXT, str(tmp_path / "counts.json"))
    assert {"tab-counts.tex", "aamas-short.tex", "counts.json"} <= {p.name for p in tmp_path.iterdir()}


def test_rough_words_round_the_section4_shares():
    from si_ext import rough_pct, rough_fraction, rough_rate, rough_under
    assert rough_pct([0.017, 0.022]) == "about 2\\%"
    assert rough_pct([0.017, 0.031]) == "about 2 to 3\\%"
    assert rough_fraction(0.567) == "more than half"
    assert rough_fraction(0.215) == "about a fifth"
    assert rough_fraction(0.26) == "about a quarter"
    assert rough_rate(0.0012) == "about 1 in 1,000"
    assert rough_rate(0.012) == "about 1 in 100"
    # (point, conservative upper bound) pairs: the bound sets the figure, so the words hold for every bound
    assert rough_under([(0.006, 0.010), (0.007, 0.012), (0.010, 0.010), (0.015, 0.015)]) == "under 2 in 100"
    assert rough_under([(0.021, 0.021)]) == "under 3 in 100"
    pairs = [(0.0064, 0.0292), (0.0065, 0.0229), (0.0099, 0.0099), (0.0154, 0.0154)]  # agent, LLM-agent, EC, AAMAS 2025
    assert rough_under(pairs) == "under 3 in 100" and all(hi < 3 / 100 for _, hi in pairs)


def test_rough_change_words_a_ratio_of_two_shares():
    from si_ext import rough_change
    assert rough_change(0.31, 0.70) == "more than doubled"
    assert rough_change(0.31, 0.50) == "rose by half"
    assert rough_change(0.31, 1.00) == "more than tripled"


def test_rough_part_words_a_part_of_a_whole():
    from si_ext import rough_part
    assert rough_part(0.519) == "about half" and rough_part(0.42) == "about half"
    assert rough_part(0.87) == "most" and rough_part(0.65) == "most"
    assert rough_part(0.26) == "about a quarter"


def test_author_draw_counts_the_first_stage_owners_code_at_the_draw():
    from si_ext import author_draw
    recs = [{"id": "q1", "owners": "several"}, {"id": "q2", "owners": "one"}, {"id": "q3", "owners": "several"}, {"id": "q4", "owners": "na"}]
    assert author_draw(recs) == "2 drawn at random among the papers it then coded several owners and 2 from the rest"


def test_author_draw_record_is_the_check_set_as_drawn():
    import json
    import subprocess
    rec = json.load(open("data/xfam/focus-check-20-draw.json"))
    assert [r["id"] for r in rec] == [x["id"] for x in json.load(open("data/xfam/focus-check-20.json"))]
    r = subprocess.run(["git", "show", "7769d46:data/xfam/focus-check-20.json"], capture_output=True, text=True)
    if r.returncode == 0:  # the commit that drew the set (absent from a fresh-history export)
        assert rec == [{"id": x["id"], "owners": x["owners"]} for x in json.loads(r.stdout)]


def test_showcase_max_is_the_largest_number_of_pages_from_one_showcase():
    from si_ext import showcase_max
    assert showcase_max([{"source": "A"}, {"source": "B"}, {"source": "A"}]) == "2"
