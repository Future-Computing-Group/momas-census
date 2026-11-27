import json
import re

from xfam_inputs import ENUMS, KEYS, build, call, schema

CODEBOOK = open("codebook-v3.md").read()


def test_keys_follow_the_codebook_output_line():
    line = next(l for l in CODEBOOK.splitlines() if l.startswith("Output one JSON object"))
    assert KEYS == re.findall(r'"(\w+)"', line)


def test_every_enum_value_is_named_in_the_codebook():
    for k, vals in ENUMS.items():
        for v in vals:
            assert v in CODEBOOK, (k, v)


def test_schema_pins_the_id_and_requires_every_key():
    s = schema("x00042")
    assert s["required"] == KEYS and s["additionalProperties"] is False
    assert s["properties"]["id"] == {"type": "string", "const": "x00042"}
    assert s["properties"]["owners"]["enum"] == ["one", "several", "na"]
    assert s["properties"]["focus"]["enum"] == ["agent", "interaction", "na"]
    assert KEYS.index("focus") == KEYS.index("cross_vendor") + 1
    assert KEYS[KEYS.index("interests") + 1:KEYS.index("owners")] == ["has_decision_maker", "faces_other_parties", "faces_quote", "one_party_runs_all"]
    assert s["properties"]["faces_other_parties"]["enum"] == ["yes", "no"] and s["properties"]["faces_quote"] == {"type": "string"}
    assert s["properties"]["quote"] == {"type": "string"}


def test_call_shows_no_venue_year_track_or_sample_id():
    it = {"xid": "x00001", "venue": "neurips-2025", "main_track": True, "title": "T", "abstract": "A " * 2000, "sample_id": "q0001"}
    c = call(it, CODEBOOK)
    assert c["call_id"] == "x00001"
    assert c["messages"][0]["content"].startswith(CODEBOOK)
    assert c["messages"][1]["content"] == "Title: T\n\nAbstract: " + it["abstract"]
    blob = json.dumps(c["messages"])
    assert "neurips" not in blob and "2025" not in blob and "q0001" not in blob
    assert set(c) == {"call_id", "schema", "messages"}


def test_build_shuffles_ids_keeps_ec_paratext_and_maps_sample_ids():
    raw = {
        "neurips-2020": [{"name": "A paper", "abstract": "a"}, {"name": "A Paper!", "abstract": "dup"}, {"name": "Front matter", "abstract": "", "type": "paratext"}],
        "ec-2025": [{"name": "E", "abstract": "e", "type": "paratext"}, {"name": "F", "abstract": "f"}],
    }
    sample = [{"id": "q0007", "venue": "neurips-2020", "title": "a paper"}]
    items = build(raw, sample, seed=1)
    assert len(items) == 3  # duplicate and ML paratext dropped, EC paratext kept
    assert sorted(i["xid"] for i in items) == ["x00001", "x00002", "x00003"]
    by_title = {i["title"]: i for i in items}
    assert by_title["A paper"]["sample_id"] == "q0007" and by_title["E"]["sample_id"] is None
    assert by_title["A paper"]["main_track"] is True
    assert build(raw, sample, seed=1) == items  # fixed seed


def test_smoke2_draws_simulated_cell_and_fresh_rest():
    from xfam_inputs import smoke2
    items = [{"xid": f"x{i:05d}", "sample_id": f"q{i}" if i % 2 else None} for i in range(1, 801)]
    sim = {f"q{i}" for i in range(1, 400, 2)}  # 200 'simulated by one owner' papers
    primary = {x["sample_id"]: ({"owners": "one", "interests": "several-aligned"} if x["sample_id"] in sim else {"owners": "One", "interests": "one"})
               for x in items if x["sample_id"]}
    primary["q401"] = {"owners": "one", "interests": "several-conflicting"}
    sim.add("q401")
    first = {x["xid"] for x in [x for x in items if x["sample_id"]][:100]}
    a, b = smoke2(items, primary, seed=3)
    assert len(a) == len(b) == 50 and not {x["xid"] for x in a} & {x["xid"] for x in b}
    assert all(x["sample_id"] in sim for x in a)
    assert all(x["sample_id"] not in sim and x["xid"] not in first for x in b)
    assert smoke2(items, primary, seed=3) == (a, b)


def test_build_keeps_a_main_track_paper_main_when_its_first_listing_is_a_satellite_session():
    # NeurIPS 2025 lists Mexico City orals under group Conference-cdmx as well as under the main Conference group
    raw = {"neurips-2025": [{"name": "P", "abstract": "p", "sourceurl": "cdmx-https://openreview.net/group?id=NeurIPS.cc/2025/Conference-cdmx"},
                            {"name": "P", "abstract": "p", "sourceurl": "https://openreview.net/group?id=NeurIPS.cc/2025/Conference"},
                            {"name": "D", "abstract": "d", "sourceurl": "https://openreview.net/group?id=NeurIPS.cc/2025/Datasets_and_Benchmarks_Track"}]}
    by_title = {i["title"]: i for i in build(raw, [], seed=1)}
    assert by_title["P"]["main_track"] is True and by_title["D"]["main_track"] is False


def test_ext_items_take_main_track_only_with_ids_that_cannot_collide_with_the_full_run():
    from xfam_inputs import ext_items
    raw = {"iclr-2025": [{"name": "M", "abstract": "m", "sourceurl": "https://openreview.net/group?id=ICLR.cc/2025/Conference"},
                         {"name": "T", "abstract": "t", "sourceurl": "https://openreview.net/group?id=TMLR"},
                         {"name": "B", "abstract": "b", "sourceurl": "https://openreview.net/group?id=ICLR.cc/2025/BlogPosts"}],
           "aamas-2025": [{"name": "A", "abstract": "a", "doi": "10.65109/x"}, {"name": "A2", "abstract": "a2", "doi": "10.65109/y"}]}
    items = ext_items(raw, seed=1)
    assert sorted(i["title"] for i in items) == ["A", "A2", "M"]  # journal track and blog posts are not main-conference papers
    assert sorted(i["xid"] for i in items) == ["y00001", "y00002", "y00003"]  # the full run uses x00001..x12383
    assert all(i["main_track"] and i["sample_id"] is None for i in items)
    assert ext_items(raw, seed=1) == items


def test_ea_sensitivity_items_use_their_own_id_space_and_venue():
    from xfam_inputs import EA, ext_items
    assert EA == "aamas-2025-ea"
    items = ext_items({EA: [{"name": "E", "abstract": "e", "doi": "10.65109/e"}, {"name": "S", "abstract": "s", "doi": "10.65109/s"}]}, seed=1, prefix="z")
    assert sorted(i["xid"] for i in items) == ["z00001", "z00002"] and {i["venue"] for i in items} == {EA}
