"""Supplementary Note 3: per-year share of papers in neighbouring fields that discuss interacting AI agents (OpenAlex).

Writes data/bibliometric.json (counts, totals, per-10,000 rates, query, retrieval date). Needs OPENALEX_API_KEY.
"""
import datetime
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

# The Perspective's canonical fields, each as the OpenAlex subfield (primary_topic.subfield) where most of its seed papers sit
# (the seeds of the citation-link analysis, data/fields/seeds-broad.json). Mechanism design (6 of 7 seeds)
# and the economics of learning (4 of 8) share subfield 1803, so they are one row; the AI literatures (20 of 38 seeds) are the reference.
# Political science's seeds scatter (3 of 8 in 3321 Public Administration, the rest across four subfields), so it is the union of
# 3320 Political Science and International Relations and 3321 Public Administration (3321 alone gives 0 to 5 papers a year).
# Distributed computing is the union of the OpenAlex topics (primary_topic.id) that match the chapters of van Steen and Tanenbaum,
# Distributed Systems, 4th ed. (2023; version 4.03), rather than subfield 1705, which is mostly networking and misses security and cloud.
# Selection read from each topic's name, description and keywords; topics that are
# mainly networking hardware, wireless, storage hardware or organisational security are left out. Subfield-1705 data: data/bibliometric-subfield-2026-11-09.json.
DC_AREAS = {"Architectures": "T10715|T10742|T10101|T10270", "Processes": "T14067|T12203", "Communication": "T10679",
            "Coordination": "T10772", "Naming": "T10742|T11478", "Consistency and replication": "T10772|T11478",
            "Fault tolerance": "T10772|T12127", "Security": "T10237|T11504|T10927|T10400|T11614"}
def area_union(areas):
    return "|".join(sorted({t for ts in areas.values() for t in ts.split("|")}))


DC_TOPICS = area_union(DC_AREAS)
# Run 4 (2026-11-09; fields/README.md): economics, control, law and political science broadened by
# reference works. Economics is the union of 2002 Economics and Econometrics and 1803 Management Science and OR, where 16 of the 19
# economics-of-the-rules seeds and 6 of the 8 economics-of-learning seeds sit (1803 alone: data/bibliometric-dcbroad-2026-11-09.json).
# Control, law and political science keep their subfields, which hold the reference works' areas; per-area rates use the OpenAlex topics
# that match each area (selection read from names, descriptions and keywords in data/bibliometric-topics-2026-11-09.json). Topics outside
# the row's subfields are marked by their subfield in the README.
AREAS = {
    "Economics": {  # Viscusi, Harrington and Sappington, 5th ed. (2018); Mas-Colell, Whinston and Green (1995), chs 14 and 23
        "Mechanism design and contracts": "T11182|T10991", "Collusion, mergers and antitrust": "T11043",
        "Platforms and the new economy": "T11437", "Capture, lobbying and law and economics": "T12225|T11762",
        "Telecommunications regulation": "T11499", "Health, safety and environmental regulation": "T10471|T10841",
        "Behavioural economics": "T10646"},
    "Distributed computing": DC_AREAS,
    "Law": {  # Oxford Handbook of Law, Regulation and Technology (2017); Restatement (Third) of Agency; competition law
        "Technology law and regulation": "T13364|T13475", "Privacy and data protection": "T11045", "Contract and consumer law": "T12374",
        "Conflict of laws": "T12767", "Intellectual property": "T13842", "Criminal law and cybercrime": "T12519", "Competition law": "T11043"},
    "Political science": {  # Oxford Handbook of Regulation (2010); Oxford Handbook of AI Governance (2022/2024)
        "Regulatory state and compliance": "T12185", "Lobbying and capture": "T12225",
        "Global regulation and international law": "T10749|T12156|T10289", "AI governance": "T10883"},
    "Control": {  # Astrom and Murray, Feedback Systems, 2nd ed.; Ljung, System Identification, 2nd ed. (stochastic approximation has no 2207 topic)
        "Stability and robust control": "T12772|T10046|T11110", "Identification and estimation": "T11236",
        "Control design, frequency domain and PID": "T11081", "Nonlinear and adaptive control": "T10040"},
}
# Control's 2025 hits on the robotics topics (every OpenAlex topic in the stored topic-hit file whose name names robots)
ROBOTICS_TOPICS = ("T10653", "T13382", "T10586", "T10879", "T10571")


def robotics_share(hits):
    """'k of n': the hits on ROBOTICS_TOPICS among all hits of a row's (topic id, name, count) list."""
    return f"{sum(c for t, _, c in hits if t in ROBOTICS_TOPICS)} of {sum(c for _, _, c in hits)}"


FIELDS = [("Economics", "subfield", "1803|2002"), ("Distributed computing", "topic", DC_TOPICS),
          ("Law", "subfield", "3308"), ("Political science", "subfield", "3320|3321"), ("Control", "subfield", "2207"),
          ("Artificial intelligence (reference)", "subfield", "1702")]
SEARCH = ('("AI agents" OR "LLM agents" OR "language model agents" OR "artificial agents") AND ("multi-agent" OR "each other" OR "one another" '
          'OR "agent-to-agent" OR "interact" OR "interactions" OR "collusion" OR "cooperation" OR "negotiation" OR "conventions")')
YEARS = range(2019, 2026)


def query_url(filt, search, key, group="publication_year"):
    p = {"filter": filt, "group_by": group, "api_key": key}
    if search:
        p["search"] = search
    return "https://api.openalex.org/works?" + urllib.parse.urlencode(p)


TYPES = "article|preprint"
CONF_TYPES = TYPES + "|conference-paper"  # sensitivity: conference papers, which computing fields use heavily


def base_filter(level, fid, types=TYPES):
    return f"primary_topic.{'' if level == 'topic' else level + '.'}id:{fid},publication_year:{min(YEARS)}-{max(YEARS)},type:{types}"


def topics_url(subfield, key):
    return "https://api.openalex.org/topics?" + urllib.parse.urlencode({"filter": f"subfield.id:{subfield}", "per-page": 200, "api_key": key})


def seed_topics_url(ids, key):
    return "https://api.openalex.org/works?" + urllib.parse.urlencode({"filter": "openalex:" + "|".join(ids), "select": "id,primary_topic", "per-page": 200, "api_key": key})


def types_url(filt, key):
    return "https://api.openalex.org/works?" + urllib.parse.urlencode({"filter": filt, "group_by": "type", "api_key": key})


NEURIPS = "S4363606243"  # OpenAlex source "neural information processing systems"
COVER_YEARS = range(2022, 2026)


def coverage_filters(source, years):
    """A source's records over the years, all and those that carry references; their ratio bounds the citation links of Supplementary Note 3."""
    f = f"primary_location.source.id:{source},publication_year:{min(years)}-{max(years)}"
    return f, f + ",referenced_works_count:>0"


def per10k(hits, totals):
    return {y: 1e4 * hits.get(y, 0) / totals[y] if totals[y] else 0.0 for y in totals}


def fetch(url):
    for wait in (1, 2, 4, 8, 16, 0):  # OpenAlex answers bursts with 429; back off and retry
        try:
            return json.load(urllib.request.urlopen(url, timeout=60))
        except urllib.error.HTTPError as e:
            if e.code != 429 or not wait:
                raise
            time.sleep(wait)


def counts(filt, search, key):
    return {int(g["key"]): g["count"] for g in fetch(query_url(filt, search, key))["group_by"]}


def row(level, fid, key, types=TYPES):
    base = base_filter(level, fid, types)
    hits, tot = counts(base, SEARCH, key), counts(base, None, key)
    tot = {y: tot.get(y, 0) for y in YEARS}
    return {"level": level, "id": fid, "hits": {y: hits.get(y, 0) for y in YEARS}, "total": tot, "per10k": per10k(hits, tot)}


if __name__ == "__main__":
    key = os.environ["OPENALEX_API_KEY"]
    if sys.argv[1:2] == ["coverage"]:  # NeurIPS records carrying references, per year
        n, refs = (counts(f, None, key) for f in coverage_filters(NEURIPS, COVER_YEARS))
        json.dump({"retrieved": datetime.date.today().isoformat(), "source": NEURIPS, "n": {y: n.get(y, 0) for y in COVER_YEARS},
                   "with_refs": {y: refs.get(y, 0) for y in COVER_YEARS}}, open(sys.argv[2], "w"), indent=1)
        sys.exit()
    if sys.argv[1:2] == ["topics"]:  # topic catalogue of the given subfields, for choosing area topics (written beside the data)
        out, dest = {}, "data/bibliometric-topics-" + datetime.date.today().isoformat() + ".json"
        for sf in sys.argv[2:]:
            for t in fetch(topics_url(sf, key))["results"]:
                out[t["id"].rsplit("/", 1)[-1]] = {"name": t["display_name"], "subfield": f"{sf} {t['subfield']['display_name']}", "works": t["works_count"],
                                                   "desc": t.get("description"), "kw": [k["display_name"] for k in t.get("keywords") or []]}
        json.dump({"retrieved": datetime.date.today().isoformat(), "topics": out}, open(dest, "w"), indent=1)
        sys.exit()
    if sys.argv[1:2] == ["seedtopics"]:  # primary topic of each seed in a seeds.json (citation literatures), to map areas to topics
        seeds = json.load(open(sys.argv[2]))
        ids = [x["openalex"] for x in seeds]
        topic = {w["id"].rsplit("/", 1)[-1]: w.get("primary_topic") or {} for i in range(0, len(ids), 50)
                 for w in fetch(seed_topics_url(ids[i:i + 50], key))["results"]}
        out = [{"cluster": x["cluster"], "openalex": x["openalex"], "label": x["label"], "topic_id": (topic[x["openalex"]].get("id") or "").rsplit("/", 1)[-1],
                "topic": topic[x["openalex"]].get("display_name"), "subfield": (topic[x["openalex"]].get("subfield") or {}).get("id", "").rsplit("/", 1)[-1],
                "subfield_name": (topic[x["openalex"]].get("subfield") or {}).get("display_name")} for x in seeds]
        json.dump(out, open(sys.argv[3], "w"), indent=1)
        sys.exit()
    if sys.argv[1:2] == ["topichits"]:  # where each row's 2025 hits sit, by primary topic (top ten), to read the area rates against
        out = {}
        for name, level, fid in FIELDS:
            f = base_filter(level, fid).replace(f"{min(YEARS)}-{max(YEARS)}", str(max(YEARS)))
            out[name] = [(g["key"].rsplit("/", 1)[-1], g["key_display_name"], g["count"]) for g in fetch(query_url(f, SEARCH, key, "primary_topic.id"))["group_by"]]
            print(name, out[name][:10])
        json.dump(out, open(sys.argv[2], "w"), indent=1)
        sys.exit()
    if sys.argv[1:2] == ["types"]:  # works per type in each row, to name the conference-paper type
        for name, level, fid in FIELDS:
            print(name, [(g["key"].rsplit("/", 1)[-1], g["count"]) for g in fetch(types_url(base_filter(level, fid).rsplit(",type:", 1)[0], key))["group_by"]])
        sys.exit()
    out = {"retrieved": datetime.date.today().isoformat(), "search": SEARCH, "fields": {}}
    for name, level, fid in FIELDS:
        out["fields"][name] = row(level, fid, key)
    out["areas"] = {f: {area: row("topic", tids, key) for area, tids in areas.items()} for f, areas in AREAS.items()}
    out["area_unions"] = {f: row("topic", area_union(areas), key) for f, areas in AREAS.items() if f != "Distributed computing"}  # areas only
    out["economics_subfields"] = {sf: row("subfield", sf, key) for sf in ("1803", "2002")}  # the old row (1803) and 2002 alone, for the report
    out["conference"] = {name: row(level, fid, key, CONF_TYPES) for name, level, fid in FIELDS}
    json.dump(out, open("data/bibliometric.json", "w"), indent=1)
    for name, d in (list(out["fields"].items()) + [(f + ": " + a, d) for f, ar in out["areas"].items() for a, d in ar.items()]
                    + [(f + ": union of areas", d) for f, d in out["area_unions"].items()] + [("subfield " + k, d) for k, d in out["economics_subfields"].items()]
                    + [("conference papers in: " + n, d) for n, d in out["conference"].items()]):
        print(name, " ".join(f"{y}:{d['per10k'][y]:.1f}" for y in YEARS), d["hits"][max(YEARS)])
