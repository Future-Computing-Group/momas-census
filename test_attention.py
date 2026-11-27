from attention import by_title, venue_stats


def test_by_title_matches_on_the_space_free_normalised_title_and_keeps_the_larger_count_of_duplicates():
    items = [{"xid": "a", "title": "Using LTL<sub>f</sub> Synthesis"}, {"xid": "b", "title": "Fast & Scalable"}, {"xid": "c", "title": "Unindexed"}]
    works = [{"display_name": "Using ltlf synthesis", "cited_by_count": 3}, {"display_name": "Fast and Scalable", "cited_by_count": 9},
             {"display_name": "Fast & Scalable", "cited_by_count": 4}, {"display_name": "Fast & Scalable", "cited_by_count": 7}]
    assert by_title(items, works) == {"a": 3, "b": 7}  # "and" is a different title; duplicates keep the larger count


def test_venue_stats_compare_citation_share_with_paper_share_on_matched_papers_only():
    cites = {"p1": 10, "p2": 0, "p3": 30, "p4": 60}
    s = venue_stats(["p1", "p2", "p3", "p4", "p5"], cites, cell={"p3", "p4", "p5"}, sub={"p4"})
    assert s["n"] == 5 and s["matched"] == 4 and s["total"] == 100 and s["median"] == 20
    assert s["cell"] == {"papers": 2, "paper_share": 0.5, "citations": 90, "citation_share": 0.9}  # p5 is unmatched
    assert s["sub"] == {"papers": 1, "paper_share": 0.25, "citations": 60, "citation_share": 0.6}


def test_ratio_fragment_is_the_rounded_ratio_of_total_citations():
    from attention import ratio_fragment
    out = {"neurips-2025": {"total": 59117}, "aamas-2025": {"total": 609}}
    assert ratio_fragment(out, "neurips-2025", "aamas-2025") == "97"


def test_split_fragment_factors_multiply_to_the_ratio():
    from attention import split_fragment, ratio_fragment
    out = {"n": {"matched": 5235, "total": 59117}, "a": {"matched": 249, "total": 609}}
    s = split_fragment(out, "n", "a")
    assert s == "21 times as many papers matched in OpenAlex, each cited 4.6 times as often on average"
    assert abs(21.02 * 4.62 - float(ratio_fragment(out, "n", "a"))) < 1
