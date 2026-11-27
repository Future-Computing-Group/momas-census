"""Fetch the paper frames into data/raw/ (skips files that exist) and check them against data/raw-manifest.json; with
--delineation, also write data/frames-delineation.json (the fields the SI frame table reads) from the checked lists.

NeurIPS, ICML and ICLR: the conferences' virtual-site lists. EC 2025: OpenAlex works of source S4363608973 (ACM EC), publication
year 2025, abstracts rebuilt from the inverted index; needs OPENALEX_API_KEY in the environment. AAMAS 2025: the full papers
are the Research Paper Track section of the IFAAMAS table of contents; their abstracts are the publisher's Crossref deposits
(DOI prefix 10.65109), matched to the contents by first page and title.
"""
import hashlib
import html
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

from census import norm

RAW = Path("data/raw")
VIRTUAL = "https://{c}.cc/static/virtual/data/{c}-{y}-orals-posters.json"
OPENALEX = "https://api.openalex.org/works?filter=primary_location.source.id:S4363608973,publication_year:2025&per-page=200&cursor={cur}&select=id,display_name,abstract_inverted_index,type&api_key={key}"
FRAMES = ["neurips-2020", "icml-2020", "neurips-2025", "icml-2025", "ec-2025", "iclr-2025", "aamas-2025", "aamas-2025-ea"]
AAMAS = "https://www.ifaamas.org/Proceedings/aamas2025/"
CROSSREF = "https://api.crossref.org/prefixes/10.65109/works?filter=from-pub-date:2025-01-01,until-pub-date:2025-12-31&rows=1000&select=DOI,title,page,abstract&cursor={cur}"
FULL = "Research Paper Track"
MIN_FULL_PAGES = 6  # research-track papers run 7 to 10 pages; extended abstracts, demos and doctoral papers 2 to 6
EA_SECTIONS = ("Extended Abstracts", "Blue Sky Ideas")  # the AAMAS sensitivity population (aamas-2025-ea), outside the headline


def abstract(inv):
    if not inv:
        return ""
    pos = {i: w for w, ix in inv.items() for i in ix}
    return " ".join(pos[i] for i in sorted(pos))


def text(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


def squash(title):
    """Title key without spaces: TOC markup such as LTL<sub>f</sub> splits a word that Crossref writes as ltlf."""
    return norm(text(title)).replace(" ", "")


def aamas_records(toc, crossref, sections=(FULL,), min_pages=MIN_FULL_PAGES):
    """Papers of the contents sections (default: the full papers of FULL), each with its Crossref abstract (same first page and same title)."""
    cut = [(m.start(), m.end()) for m in re.finditer(r'<a name="\d+" id="\d+"></a>', toc)] + [(len(toc), len(toc))]
    by_page = {int(c["page"].split("-")[0]): c for c in crossref}
    out = []
    for (_, a), (b, _) in zip(cut, cut[1:]):
        sec = next((x for x in sections if text(toc[a:b]).startswith(x)), None)
        if sec is None:
            continue
        for p, t, pg in re.findall(r'<a href="\.\./pdfs/p(\d+)\.pdf"[^>]*>(.*?)</a>\s*&nbsp;<font[^>]*>\(Page\s+(\d+)\)', toc[a:b], re.S):
            c = by_page.get(int(p))
            assert p == pg and c and squash(c["title"][0]) == squash(t), f"no Crossref record for page {p}: {text(t)}"
            first, last = map(int, c["page"].split("-"))
            assert last - first + 1 >= min_pages, f"page {p} has {last - first + 1} pages: not a full paper"
            out.append({"name": text(t), "abstract": text(c["abstract"]), "doi": c["DOI"], "pages": c["page"], "section": sec, "pdf": f"{AAMAS}pdfs/p{p}.pdf"})
    return out


def get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "interaction-time-census"}), timeout=60).read()


def fetch(frame):
    if frame.startswith("ec-"):
        rows, cur = [], "*"
        while cur:
            d = json.loads(get(OPENALEX.format(cur=cur, key=os.environ["OPENALEX_API_KEY"])))
            rows += [{"name": w["display_name"], "abstract": abstract(w.get("abstract_inverted_index")), "openalex": w["id"], "type": w.get("type")} for w in d["results"]]
            cur = d["meta"].get("next_cursor")
        return json.dumps(rows).encode()
    if frame.startswith("aamas-2025"):
        toc = get(AAMAS + "forms/contents.htm").decode("latin-1")
        rows, cur = [], "*"
        while True:
            d = json.loads(get(CROSSREF.format(cur=urllib.parse.quote(cur))))["message"]
            if not d["items"]:
                break
            rows, cur = rows + d["items"], d["next-cursor"]
            time.sleep(2)  # polite
        recs = aamas_records(toc, rows) if frame == "aamas-2025" else aamas_records(toc, rows, sections=EA_SECTIONS, min_pages=1)
        return json.dumps(recs, ensure_ascii=False).encode()
    c, y = frame.split("-")
    return get(VIRTUAL.format(c=c, y=y))


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


# The raw lists carry author records (names, institutions, bios, some e-mail addresses); the release keeps only the fields that the
# SI frame table (si_tables.py, Table S2) reads, so that table regenerates without them. The raw lists stay checkable by sha256.
DELINEATION = Path("data/frames-delineation.json")
DELINEATED = ["neurips-2020", "icml-2020", "neurips-2025", "icml-2025", "ec-2025"]
KEEP = ("name", "sourceurl", "type")


def delineation(records):
    """Each record's title, OpenReview group and OpenAlex type, in order (absent or null fields left out)."""
    return [{k: r[k] for k in KEEP if r.get(k) is not None} for r in records]


def delineation_record():
    out = {}
    for v in DELINEATED:
        d = json.load(open(RAW / f"{v}.json"))
        out[v] = delineation(d["results"] if isinstance(d, dict) else d)
    return out


if __name__ == "__main__":
    RAW.mkdir(parents=True, exist_ok=True)
    for f in FRAMES:
        p = RAW / f"{f}.json"
        if not p.exists():
            p.write_bytes(fetch(f))
    if sys.argv[1:] == ["--write-manifest"]:
        old = json.load(open("data/raw-manifest.json"))  # archived frames are never re-pinned: only new frames are added
        json.dump({f: old.get(f) or sha(RAW / f"{f}.json") for f in FRAMES}, open("data/raw-manifest.json", "w"), indent=1)
    want = json.load(open("data/raw-manifest.json"))
    bad = [f for f in FRAMES if sha(RAW / f"{f}.json") != want[f]]
    print("raw frames match the manifest" if not bad else f"differ from the archived frames: {bad} (the live lists change after the conference)")
    if sys.argv[1:] == ["--delineation"] and not bad:
        json.dump(delineation_record(), open(DELINEATION, "w"), indent=0, ensure_ascii=False)
