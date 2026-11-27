from affil import sector, paper_group


def test_sector_industry_academic_unknown():
    assert sector("Google DeepMind") == "industry"
    assert sector("Microsoft Research Asia") == "industry"
    assert sector("ByteDance Inc.") == "industry"
    assert sector("Huawei Technologies Ltd.") == "industry"
    assert sector("Peking University") == "academic"
    assert sector("Massachusetts Institute of Technology") == "academic"
    assert sector("MIT") == "academic"
    assert sector("Max Planck Institute for Intelligent Systems") == "academic"
    assert sector("Shanghai AI Laboratory") == "academic"  # public research lab
    assert sector("") == "unknown" and sector(None) == "unknown"
    assert sector("Zorblax") == "unknown"
    # a university-affiliated company string is industry (industry rule precedes)
    assert sector("Google; Stanford University") == "industry"


def test_paper_group():
    assert paper_group(["industry", "academic"]) == "mixed"
    assert paper_group(["industry", "unknown"]) == "industry"
    assert paper_group(["academic", "academic"]) == "academic"
    assert paper_group(["unknown"]) == "unknown"


def test_short_academic_names_and_ibm():
    for s in ("UC Berkeley", "Stanford", "Technion", "UIUC", "UT Austin", "Politecnico di Milano", "Caltech", "KU Leuven", "Virginia Tech", "POSTECH", "Georgia Tech", "Tsinghua"):
        assert sector(s) == "academic", s
    assert sector("International Business Machines") == "industry"


def test_fisher_two_sided_known_value():
    from affil import fisher
    # 2x2 [[1, 9], [11, 3]]: two-sided p = 0.002759 (classic tea-tasting-style example)
    assert abs(fisher(1, 10, 11, 14) - 0.002759) < 1e-5
    assert abs(fisher(5, 10, 5, 10) - 1.0) < 1e-9


def test_alphabetical_detection():
    from affil import alphabetical
    assert alphabetical(["Ann Adams", "Bob Brown", "Cy Cohen"])
    assert not alphabetical(["Bob Brown", "Ann Adams", "Cy Cohen"])
    assert not alphabetical(["Ann Adams"])  # single author: undefined, not alphabetical
    assert alphabetical(["K. Smith", "J. de Vries"])  # surname = last token: smith < vries


def test_position_sector_and_industry_share():
    from affil import position_sectors
    authors = [{"fullname": "A B", "institution": "Peking University"}, {"fullname": "C D", "institution": "Google"}, {"fullname": "E F", "institution": "Meta"}]
    ps = position_sectors(authors)
    assert ps["first"] == "academic" and ps["last"] == "industry"
    assert ps["share"] == "majority" and ps["n"] == 3
    assert position_sectors([{"fullname": "A B", "institution": "MIT"}])["share"] == "none"


def test_dual_affiliation_sensitivity():
    # default: an institution string naming a company and a university counts as industry; the sensitivity can send it elsewhere
    assert sector("Google; Stanford University", dual="academic") == "academic"
    assert sector("Google; Stanford University", dual="unknown") == "unknown"
    assert sector("Google DeepMind", dual="academic") == "industry"
    assert sector("Stanford University", dual="unknown") == "academic"
