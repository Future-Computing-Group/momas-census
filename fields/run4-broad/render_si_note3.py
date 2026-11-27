"""Render the Supplementary Note 3 table files from data/bibliometric.json into a given folder, with the row formatting of
si_tables.py, without running si_tables.py. Usage: python3 -s -E render_si_note3.py <bibliometric.json> <out dir>"""
import json, pathlib, re, sys

SHOW = ["2019", "2021", "2023", "2024", "2025"]


def rows(named):
    return "\n".join(f"{name} & " + " & ".join(f"{d['per10k'][y]:.1f}" for y in SHOW) + f" & {d['hits']['2025']:,} \\\\" for name, d in named) + "\n"


bib = json.load(open(sys.argv[1]))
out = pathlib.Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
(out / "tab-bibliometric.tex").write_text(rows(bib["fields"].items()))
(out / "bibliometric-date.tex").write_text(bib["retrieved"])
(out / "tab-bibliometric-conference.tex").write_text(rows(bib["conference"].items()))
for field, areas in bib["areas"].items():
    slug = re.sub(r"[^a-z]+", "-", field.lower()).strip("-")
    union = [("Union of the areas", bib["area_unions"][field])] if field in bib.get("area_unions", {}) else []
    (out / f"tab-bibliometric-{slug}-areas.tex").write_text(rows(list(areas.items()) + union))
print("wrote", sorted(p.name for p in out.iterdir() if p.suffix == ".tex"))
