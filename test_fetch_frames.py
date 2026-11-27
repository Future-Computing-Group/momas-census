import json
import os

import pytest

from fetch_frames import FRAMES, VIRTUAL, aamas_records

TOC = """<a name="1" id="1"></a>Keynote Talks
<a href="../pdfs/p1.pdf" style="x">A Keynote</a>&nbsp;<font size="1">(Page 1)</font>
<a name="2" id="2"></a>Research Paper Track
<a href="../pdfs/p5.pdf" style="x">Enhancing
  Offline RL</a>&nbsp;<font size="1">(Page
  5)</font>
<a href="../pdfs/p14.pdf" style="x">Fast &amp; Scalable</a>&nbsp;<font size="1">(Page 14)</font>
<a name="3" id="3"></a>Extended Abstracts
<a href="../pdfs/p2500.pdf" style="x">An Extended Abstract</a>&nbsp;<font size="1">(Page 2500)</font>
"""
CR = [
    {"DOI": "10.65109/aaaa", "title": ["Enhancing Offline RL"], "page": "5-13", "abstract": "<jats:p>First &amp; para.</jats:p>\n<jats:p>Second  para.</jats:p>"},
    {"DOI": "10.65109/bbbb", "title": ["Fast &amp; Scalable"], "page": "14-23", "abstract": "<jats:p>B.</jats:p>"},
    {"DOI": "10.65109/cccc", "title": ["An Extended Abstract"], "page": "2500-2502", "abstract": "<jats:p>E.</jats:p>"},
    {"DOI": "10.65109/dddd", "title": ["A Keynote"], "page": "1-2", "abstract": "<jats:p>K.</jats:p>"},
]


def test_frames_add_iclr_and_aamas_2025_and_iclr_uses_the_virtual_site_list():
    assert FRAMES[5:7] == ["iclr-2025", "aamas-2025"]
    assert VIRTUAL.format(c="iclr", y="2025") == "https://iclr.cc/static/virtual/data/iclr-2025-orals-posters.json"


def test_aamas_records_keep_only_research_track_full_papers_with_the_publisher_abstract():
    recs = aamas_records(TOC, CR)
    assert [r["name"] for r in recs] == ["Enhancing Offline RL", "Fast & Scalable"]
    assert recs[0]["abstract"] == "First & para. Second para."
    assert recs[0] == {"name": "Enhancing Offline RL", "abstract": "First & para. Second para.", "doi": "10.65109/aaaa", "pages": "5-13",
                       "section": "Research Paper Track", "pdf": "https://www.ifaamas.org/Proceedings/aamas2025/pdfs/p5.pdf"}


def test_aamas_records_refuse_a_research_paper_without_a_matching_abstract():
    with pytest.raises(AssertionError):
        aamas_records(TOC, [c for c in CR if c["DOI"] != "10.65109/bbbb"])
    renamed = [{**c, "title": ["Something else"]} if c["DOI"] == "10.65109/bbbb" else c for c in CR]
    with pytest.raises(AssertionError):
        aamas_records(TOC, renamed)


def test_aamas_records_refuse_a_short_paper_listed_as_a_full_paper():
    short = [{**c, "page": "14-16"} if c["DOI"] == "10.65109/bbbb" else c for c in CR]
    with pytest.raises(AssertionError):
        aamas_records(TOC, short)  # 3 pages is an extended abstract


def test_aamas_sensitivity_frame_takes_extended_abstracts_and_blue_sky_without_a_page_floor():
    from fetch_frames import EA_SECTIONS, FRAMES
    assert FRAMES[-1] == "aamas-2025-ea" and EA_SECTIONS == ("Extended Abstracts", "Blue Sky Ideas")
    recs = aamas_records(TOC, CR, sections=EA_SECTIONS, min_pages=1)
    assert [(r["name"], r["section"], r["doi"]) for r in recs] == [("An Extended Abstract", "Extended Abstracts", "10.65109/cccc")]
    assert aamas_records(TOC, CR) == aamas_records(TOC, CR, sections=("Research Paper Track",), min_pages=6)  # the headline frame is unchanged


def test_aamas_records_match_a_title_whose_subscript_markup_splits_a_word():
    toc = TOC.replace("An Extended Abstract</a>", "Using LTL<sub>f</sub> Synthesis</a>")
    cr = [{**c, "title": ["Using ltlf Synthesis"]} if c["DOI"] == "10.65109/cccc" else c for c in CR]
    assert [r["doi"] for r in aamas_records(toc, cr, sections=("Extended Abstracts",), min_pages=1)] == ["10.65109/cccc"]


def test_delineation_keeps_only_the_fields_the_frame_table_reads():
    from fetch_frames import delineation
    recs = [{"name": "A", "sourceurl": "https://openreview.net/group?id=X/Conference", "authors": [{"institution": "a@b.c"}], "abstract": "t"},
            {"name": "B", "sourceurl": None, "type": "paratext", "bio": "x"}]
    assert delineation(recs) == [{"name": "A", "sourceurl": "https://openreview.net/group?id=X/Conference"}, {"name": "B", "type": "paratext"}]


@pytest.mark.skipif(not all(os.path.exists(f"data/raw/{v}.json") for v in ("neurips-2020", "icml-2020", "neurips-2025", "icml-2025", "ec-2025")),
                    reason="needs the raw frames (fetch_frames.py)")
def test_committed_delineation_is_the_reduction_of_the_raw_frames():
    from fetch_frames import DELINEATION, delineation_record
    assert json.load(open(DELINEATION)) == delineation_record()
