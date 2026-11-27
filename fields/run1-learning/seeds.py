"""Step 1: resolve seeds by DOI (arXiv DOIs for arXiv papers) in one batched filter call per 50; title fallback only for misses."""
import json, os
from oa import get, sid

D = os.path.dirname(os.path.abspath(__file__))
AX = "10.48550/arxiv."
# (cluster, short label, doi, expected title fragment)
SEEDS = [
    ("C1", "Perdomo et al. 2020, Performative prediction", AX + "2002.06673", "performative prediction"),
    ("C1", "Hardt et al. 2016, Strategic classification", "10.1145/2840728.2840730", "strategic classification"),
    ("C1", "Mendler-Dunner et al. 2020, Stochastic optimization for PP", AX + "2006.06887", "stochastic optimization for performative"),
    ("C1", "Miller, Perdomo, Zrnic 2021, Outside the echo chamber", AX + "2102.08570", "echo chamber"),
    ("C1", "Jagadeesan et al. 2021, Alternative microfoundations", AX + "2106.12705", "microfoundations"),
    ("C1", "Brown, Hod, Kalemaj 2022, PP in a stateful world", AX + "2011.03885", "stateful"),
    ("C1", "Hardt, Jagadeesan, Mendler-Dunner 2022, Performative power", AX + "2203.17232", "performative power"),
    ("C1", "Zrnic et al. 2021, Who leads and who follows", AX + "2106.12529", "who leads"),
    ("C2", "Hernandez-Leal et al. 2017, non-stationarity survey", AX + "1707.09183", "non-stationarity"),
    ("C2", "Foerster et al. 2018, LOLA", AX + "1709.04326", "opponent-learning awareness"),
    ("C2", "Kim et al. 2021, Meta-MAPG", AX + "2011.00382", "policy gradient"),
    ("C2", "Lu et al. 2022, M-FOS", AX + "2205.01447", "opponent shaping"),
    ("C2", "Lowe et al. 2017, MADDPG", AX + "1706.02275", "actor-critic"),
    ("C2", "Papoudakis et al. 2019, non-stationarity in MARL", AX + "1906.04737", "non-stationarity"),
    ("C2", "Panait and Luke 2005, cooperative MAL", "10.1007/s10458-005-2631-2", "cooperative multi-agent learning"),
    ("C3", "Deng, Schneider, Sivan 2019, Strategizing vs no-regret", AX + "1909.13861", "no-regret"),
    ("C3", "Braverman et al. 2018, Selling to a no-regret buyer", "10.1145/3219166.3219233", "no-regret buyer"),
    ("C3", "Banchio and Skrzypacz 2022, AI and auction design", "10.1145/3490486.3538244", "auction design"),
    ("C3", "Arora, Dekel, Tewari 2012, adaptive adversary", AX + "1206.6400", "adaptive adversary"),
    ("C3", "Hart and Mas-Colell 2003, Uncoupled dynamics", "10.1257/000282803322655581", "uncoupled dynamics"),
    ("C3", "Arunachaleswaran et al. 2024, Pareto-optimal algorithms", AX + "2402.09549", "pareto-optimal"),
    ("C3", "Zhang et al. 2023, Steering no-regret learners", AX + "2306.05221", "steering"),
    ("C3", "Shoham, Powers, Grenager 2007, If MAL is the answer", "10.1016/j.artint.2006.02.006", "multi-agent learning"),
    ("C4", "Hammond et al. 2025, Multi-agent risks", AX + "2502.14143", "multi-agent risks"),
    ("C4", "Leibo et al. 2019, Autocurricula", AX + "1903.00742", "autocurricula"),
    ("C4", "Carroll et al. 2022, induced preference shifts", AX + "2204.11966", "preference shift"),
    ("C4", "Mirsky et al. 2022, ad hoc teamwork survey", AX + "2202.10450", "ad hoc teamwork"),
    ("C4", "Stone et al. 2010, Ad hoc autonomous agent teams", "10.1609/aaai.v24i1.7529", "ad hoc autonomous"),
    ("C4", "Zheng et al. 2022, AI Economist", "10.1126/sciadv.abk2607", "ai economist"),
    ("C4", "Sourbut, Hammond, Wood 2024, delegation games", AX + "2402.15821", "delegation games"),
    ("C5", "Shumailov et al. 2024, AI models collapse (Nature version of the 2023 arXiv paper)", "10.1038/s41586-024-07566-y", "recursively generated"),
    ("C5", "Gerstgrasser et al. 2024, Is model collapse inevitable", AX + "2404.01413", "model collapse"),
    ("C5", "Bertrand et al. 2024, iterative retraining stability", AX + "2310.00429", "iterative retraining"),
    ("C5", "Taori and Hashimoto 2023, Data feedback loops", AX + "2209.03942", "feedback loops"),
    ("C5", "Ensign et al. 2018, Runaway feedback loops", AX + "1706.09847", "runaway feedback"),
    ("C5", "Chaney et al. 2018, Algorithmic confounding", "10.1145/3240323.3240370", "algorithmic confounding"),
    ("C5", "Jiang et al. 2019, Degenerate feedback loops", "10.1145/3306618.3314288", "degenerate feedback"),
    ("C5", "Brennan et al. 2023, Symbiosis bias in A/B tests", AX + "2309.07107", "symbiosis"),
    ("C6", "Lucas 1976, Econometric policy evaluation", "10.1016/s0167-2231(76)80003-6", "econometric policy evaluation"),
    ("C6", "Marcet and Sargent 1989, least squares learning", "10.1016/0022-0531(89)90123-0", "least squares learning"),
    ("C6", "Evans and Honkapohja 2003, optimal monetary policies", "10.1111/1467-937x.00270", "monetary"),
    ("C6", "Cho, Williams, Sargent 2002, Escaping Nash inflation", "10.1111/1467-937x.00196", "nash inflation"),
    ("C6", "Esponda and Pouzo 2016, Berk-Nash equilibrium", "10.3982/ecta12609", "berk"),
    ("C6", "Bolton and Harris 1999, Strategic experimentation", "10.1111/1468-0262.00022", "strategic experimentation"),
    ("C6", "Keller, Rady, Cripps 2005, exponential bandits", "10.1111/j.1468-0262.2005.00564.x", "exponential bandits"),
    ("C6", "Fudenberg and Levine 1993, Self-confirming equilibrium", "10.2307/2951716", "self-confirming"),
    ("C7", "Forssell and Ljung 1999, Closed-loop identification revisited", "10.1016/s0005-1098(99)00022-9", "closed-loop identification"),
    ("C7", "Gevers 2005, Identification for control", "10.3166/ejc.11.335-352", "identification for control"),
    ("C7", "Bombois et al. 2006, Least costly identification", "10.1016/j.automatica.2006.05.016", "least costly"),
    ("C7", "Rojas et al. 2007, Robust optimal experiment design", "10.1016/j.automatica.2006.12.013", "experiment design"),
    ("C7", "Weerts, Van den Hof, Dankers 2018, network identifiability", "10.1016/j.automatica.2017.12.013", "identifiability"),
    ("C7", "Hendrickx, Gevers, Bazanella 2019, partial node measurements", "10.1109/tac.2018.2867336", "identifiability"),
    ("C7", "Cheng, Shi, Van den Hof 2022, allocation of excitation", "10.1109/tac.2021.3063237", "excitation"),
    ("C7", "van Waarde et al. 2020, Data informativity", "10.1109/tac.2019.2959924", "informativity"),
    ("F1", "Pedreschi, Ruggieri, Turini 2008, Discrimination-aware data mining", "10.1145/1401890.1401959", "discrimination-aware"),
    ("F1", "Kamiran and Calders 2012, Data preprocessing without discrimination", "10.1007/s10115-011-0463-8", "without discrimination"),
    ("F2", "Dwork et al. 2012, Fairness through awareness", "10.1145/2090236.2090255", "fairness through awareness"),
    ("F2", "Zemel et al. 2013, Learning fair representations", None, "learning fair representations"),
    ("F3", "Barocas and Selbst 2016, Big data's disparate impact", "10.15779/z38bg31", "disparate impact"),
    ("F3", "Sweeney 2013, Discrimination in online ad delivery", "10.1145/2460276.2460278", "online ad delivery"),
]
SEARCH = {
    "Shumailov et al. 2023, Curse of recursion": "curse of recursion training on generated data makes models forget",
    "Marcet and Sargent 1989, least squares learning": "convergence of least squares learning mechanisms in self-referential linear stochastic models",
    "Evans and Honkapohja 2003, optimal monetary policies": "expectations and the stability problem for optimal monetary policies",
    "Cheng, Shi, Van den Hof 2022, allocation of excitation": "allocation of excitation signals for generic identifiability of linear dynamic networks",
    "van Waarde et al. 2020, Data informativity": "data informativity a new perspective on data-driven analysis and control",
    "Zemel et al. 2013, Learning fair representations": "learning fair representations",
}
SEL = "id,doi,title,publication_year,cited_by_count,ids"


def resolve():
    dois = [s[2] for s in SEEDS if s[2]]
    batch = [w for i in range(0, len(dois), 50) for w in
             get("works", filter="doi:" + "|".join(dois[i:i + 50]), select=SEL, **{"per-page": 200})["results"]]
    out = []
    for c, lab, doi, frag in SEEDS:
        m = [w for w in batch if frag in (w.get("title") or "").lower()]
        exact = [w for w in m if doi and (w.get("doi") or "").lower().endswith(doi.lower())]
        m = exact or m
        w, how = (m[0], "doi") if len(m) == 1 else (None, None)
        if w is None:  # fallback: title search (10 credits); only for misses
            res = get("works", filter="title.search:" + SEARCH[lab], select=SEL, **{"per-page": 5})["results"]
            res = [r for r in res if frag in (r.get("title") or "").lower()]
            w = max(res, key=lambda r: r["cited_by_count"]) if res else None
            how = "title-search"
        out.append({"cluster": c, "label": lab, "doi_tried": doi, "how": how,
                    "openalex": sid(w["id"]) if w else None, "oa_title": w["title"] if w else None,
                    "oa_year": w["publication_year"] if w else None, "cited_by": w["cited_by_count"] if w else None})
    json.dump(out, open(os.path.join(D, "seeds.json"), "w"), indent=1)
    return out


if __name__ == "__main__":
    for s in resolve():
        print(s["cluster"], s["how"], s["openalex"], s["oa_year"], s["cited_by"], "|", s["label"], "|", s["oa_title"])
