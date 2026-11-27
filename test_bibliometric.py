from bibliometric import per10k, query_url


def test_per10k_handles_missing_years_and_zero_totals():
    assert per10k({2024: 3}, {2024: 10000, 2025: 0}) == {2024: 3.0, 2025: 0.0}


def test_query_url_carries_filter_search_and_grouping_but_no_email():
    u = query_url("primary_topic.field.id:20", "x AND y", "KEY")
    assert "group_by=publication_year" in u and "search=x+AND+y" in u and "api_key=KEY" in u and "mailto" not in u


def test_base_filter_uses_the_level_of_each_row():
    from bibliometric import base_filter
    assert base_filter("subfield", "1803") == "primary_topic.subfield.id:1803,publication_year:2019-2025,type:article|preprint"
    assert base_filter("field", "17").startswith("primary_topic.field.id:17,")


def test_fields_carry_name_level_id_and_end_with_the_reference_row():
    from bibliometric import FIELDS
    assert all(len(r) == 3 and r[1] in ("field", "subfield", "topic") and all(p.lstrip("T").isdigit() for p in r[2].split("|")) for r in FIELDS)
    assert "reference" in FIELDS[-1][0]


def test_no_email_in_any_url():
    from bibliometric import base_filter
    for name, level, fid in __import__("bibliometric").FIELDS:
        u = query_url(base_filter(level, fid), "x", "KEY")
        assert "mailto" not in u and "@" not in u and "email" not in u


def test_a_field_can_be_the_union_of_two_subfields():
    from bibliometric import base_filter
    assert base_filter("subfield", "3320|3321").startswith("primary_topic.subfield.id:3320|3321")


def test_a_topic_row_filters_on_the_primary_topic_id_union():
    from bibliometric import base_filter
    assert base_filter("topic", "T10772|T10742") == "primary_topic.id:T10772|T10742,publication_year:2019-2025,type:article|preprint"


def test_distributed_computing_is_the_union_of_the_textbook_area_topics():
    from bibliometric import DC_AREAS, FIELDS
    dc = [r for r in FIELDS if r[0] == "Distributed computing"][0]
    assert dc[1] == "topic" and set(dc[2].split("|")) == {t for ts in DC_AREAS.values() for t in ts.split("|")}
    assert all(t.startswith("T") and t[1:].isdigit() for t in dc[2].split("|"))


def test_base_filter_takes_a_type_union_for_the_conference_sensitivity():
    from bibliometric import base_filter
    assert base_filter("subfield", "2002").endswith(",type:article|preprint")
    assert base_filter("subfield", "2002", types="article|preprint|conference").endswith(",type:article|preprint|conference")


def test_topics_url_lists_a_subfields_topics_with_the_key_and_no_email():
    from bibliometric import topics_url
    u = topics_url("2002", "KEY")
    assert u.startswith("https://api.openalex.org/topics?") and "filter=subfield.id%3A2002" in u and "per-page=200" in u
    assert "api_key=KEY" in u and "mailto" not in u and "@" not in u


def test_types_url_groups_a_row_by_work_type():
    from bibliometric import types_url
    u = types_url("primary_topic.id:T10772,publication_year:2019-2025", "KEY")
    assert "group_by=type" in u and "api_key=KEY" in u and "mailto" not in u


def test_seed_topics_url_batches_openalex_ids_and_selects_the_primary_topic():
    from bibliometric import seed_topics_url
    u = seed_topics_url(["W1", "W2"], "KEY")
    assert "filter=openalex%3AW1%7CW2" in u and "select=id%2Cprimary_topic" in u and "per-page=200" in u
    assert "api_key=KEY" in u and "mailto" not in u


def test_economics_row_is_the_union_of_economics_and_econometrics_and_management_science():
    from bibliometric import FIELDS
    econ = [r for r in FIELDS if r[0].startswith("Economics")][0]
    assert econ[1] == "subfield" and set(econ[2].split("|")) == {"2002", "1803"}


def test_every_broadened_field_has_reference_work_areas_as_topic_unions():
    from bibliometric import AREAS, FIELDS
    names = {r[0] for r in FIELDS}
    assert set(AREAS) <= names and {"Distributed computing", "Control", "Law", "Political science"} <= set(AREAS)
    assert any(n.startswith("Economics") for n in AREAS)
    for field, areas in AREAS.items():
        assert areas and all(t.startswith("T") and t[1:].isdigit() for ts in areas.values() for t in ts.split("|"))


def test_conference_sensitivity_adds_the_conference_paper_type():
    from bibliometric import CONF_TYPES, TYPES
    assert CONF_TYPES == TYPES + "|conference-paper"


def test_query_url_can_group_hits_by_primary_topic():
    u = query_url("primary_topic.subfield.id:2207", "x", "KEY", group="primary_topic.id")
    assert "group_by=primary_topic.id" in u and "search=x" in u and "mailto" not in u


def test_area_union_is_the_sorted_set_of_area_topics():
    from bibliometric import DC_AREAS, DC_TOPICS, area_union
    assert area_union({"a": "T2|T1", "b": "T1"}) == "T1|T2" and area_union(DC_AREAS) == DC_TOPICS


def test_coverage_filters_name_the_source_years_and_the_reference_condition():
    from bibliometric import coverage_filters
    a, b = coverage_filters("S1", range(2022, 2026))
    assert a == "primary_location.source.id:S1,publication_year:2022-2025" and b == a + ",referenced_works_count:>0"


def test_control_robotics_share_counts_the_robotics_topics_of_the_stored_2025_hits():
    import json
    from bibliometric import ROBOTICS_TOPICS, robotics_share
    hits = json.load(open("data/bibliometric-topichits-2025-2026-11-09.json"))["Control"]
    assert all("Robot" in name for tid, name, _ in hits if tid in ROBOTICS_TOPICS)
    assert {tid for tid, name, _ in hits if "Robot" in name} == set(ROBOTICS_TOPICS)
    assert robotics_share(hits) == "143 of 253"
    assert robotics_share([("T10653", "Robot Manipulation and Learning", 3), ("T1", "Other", 5)]) == "3 of 8"
