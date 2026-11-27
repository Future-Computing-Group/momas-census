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
    ("R1", "Myerson 1981, Optimal auction design", "10.1287/moor.6.1.58", "optimal auction design"),
    ("R1", "Myerson and Satterthwaite 1983, Efficient mechanisms for bilateral trading", "10.1016/0022-0531(83)90048-0", "bilateral trading"),
    ("R1", "Myerson 1983, Mechanism design by an informed principal", "10.2307/1912116", "informed principal"),
    ("R1", "McAfee 1993, Mechanism design by competing sellers", "10.2307/2951643", "competing sellers"),
    ("R1", "Vickrey 1961, Counterspeculation, auctions, and competitive sealed tenders", "10.1111/j.1540-6261.1961.tb02789.x", "counterspeculation"),
    ("R1", "Nisan and Ronen 2001, Algorithmic mechanism design (GEB)", "10.1006/game.1999.0790", "algorithmic mechanism design"),
    ("R1", "Dutting et al. 2024, Optimal auctions through deep learning", "10.1145/3630749", "optimal auctions through deep learning"),
    ("R2", "Lamport, Shostak, Pease 1982, The Byzantine generals problem", "10.1145/357172.357176", "byzantine generals"),
    ("R2", "Dwork, Lynch, Stockmeyer 1988, Consensus under partial synchrony", "10.1145/42282.42283", "partial synchrony"),
    ("R2", "Castro and Liskov 2002, PBFT and proactive recovery", "10.1145/571637.571640", "practical byzantine fault tolerance"),
    ("R2", "Fischer, Lynch, Paterson 1985, Impossibility of consensus", "10.1145/3149.214121", "impossibility of distributed consensus"),
    ("R2", "Shneidman and Parkes 2004, Specification faithfulness", "10.1145/1011767.1011781", "specification faithfulness"),
    ("R2", "Abraham, Dolev, Gonen, Halpern 2006, Distributed computing meets game theory", "10.1145/1146381.1146393", "distributed computing meets game theory"),
    ("R2", "Aiyer et al. 2005, BAR fault tolerance", "10.1145/1095810.1095816", "bar fault tolerance"),
    ("R3", "Kolt 2025, Governing AI agents (SSRN record)", "10.2139/ssrn.4772956", "governing ai agents"),
    ("R3", "Pasquale 2015, The Black Box Society", "10.4159/harvard.9780674736061", "black box society"),
    ("R3", "Chopra and White 2011, A legal theory for autonomous artificial agents", "10.3998/mpub.356801", "legal theory for autonomous artificial agents"),
    ("R3", "Harrington 2018, Competition law for collusion by autonomous agents", "10.1093/joclec/nhy016", "collusion by autonomous artificial agents"),
    ("R3", "Ezrachi and Stucke 2016, Virtual Competition", "10.4159/9780674973336", "virtual competition"),
    ("R3", "Cobbe, Veale, Singh 2023, Accountability in algorithmic supply chains", "10.1145/3593013.3594073", "algorithmic supply chains"),
    ("R3", "Wachter, Mittelstadt, Floridi 2017, No right to explanation in the GDPR (SSRN record)", "10.2139/ssrn.2903469", "right to explanation"),
    ("R4", "Buthe and Mattli 2011, The New Global Rulers", "10.23943/princeton/9780691144795.001.0001", "new global rulers"),
    ("R4", "Mattli and Buthe 2003, Setting international standards", "10.1353/wp.2004.0006", "setting international standards"),
    ("R4", "Abbott and Snidal 2009, The governance triangle", "10.2307/j.ctt7rgmj.6", "governance triangle"),
    ("R4", "Buthe 2010, Private regulation in the global economy", "10.2202/1469-3569.1328", "private regulation in the global economy"),
    ("R4", "Bradford 2020, The Brussels Effect", "10.1093/oso/9780190088583.001.0001", "brussels effect"),
    ("R4", "Drezner 2004, The global governance of the Internet", "10.2307/20202392", "global governance of the internet"),
    ("R4", "Taeihagh 2021, Governance of artificial intelligence", "10.1080/14494035.2021.1928377", "governance of artificial intelligence"),
    ("R4", "Ulnicane et al. 2021, Framing governance for a contested emerging technology", "10.1080/14494035.2020.1855800", "framing governance"),
    # R2 broadened to the chapters of van Steen and Tanenbaum, Distributed Systems, 4th ed.; appended so earlier batches stay cached
    ("R2", "Saltzer, Reed, Clark 1984, End-to-end arguments (architectures)", "10.1145/357401.357402", "end-to-end arguments"),
    ("R2", "Barham et al. 2003, Xen and the art of virtualization (processes)", "10.1145/945445.945462", "xen and the art of virtualization"),
    ("R2", "Birrell and Nelson 1984, Implementing remote procedure calls (communication)", "10.1145/2080.357392", "remote procedure calls"),
    ("R2", "Lamport 1978, Time, clocks, and the ordering of events (coordination)", "10.1145/359545.359563", "time, clocks"),
    ("R2", "Chandy and Lamport 1985, Distributed snapshots (coordination)", "10.1145/214451.214456", "distributed snapshots"),
    ("R2", "Stoica et al. 2001, Chord (naming)", "10.1145/383059.383071", "chord"),
    ("R2", "Mockapetris and Dunlap 1988, Development of the domain name system (naming)", "10.1145/52324.52338", "domain name system"),
    ("R2", "Gilbert and Lynch 2002, Brewer's conjecture (CAP) (consistency and replication)", "10.1145/564585.564601", "brewer's conjecture"),
    ("R2", "Herlihy and Wing 1990, Linearizability (consistency and replication)", "10.1145/78969.78972", "linearizability"),
    ("R2", "Needham and Schroeder 1978, Using encryption for authentication (security)", "10.1145/359657.359659", "using encryption for authentication"),
    ("R2", "Burrows, Abadi, Needham 1990, A logic of authentication (security)", "10.1145/77648.77649", "logic of authentication"),
]
# Run 4: R1, C7, R3 and R4 broadened to the areas of their reference works. Kept apart from SEEDS so the
# current seeds' citer pools stay cached: fetch.py fetches the citers of these seeds separately and takes the union.
ADDED = [
    ("R1", "Cremer and McLean 1988, Full extraction of the surplus (mechanism design)", "10.2307/1913096", "full extraction of the surplus"),
    ("R1", "Holmstrom 1979, Moral hazard and observability (principal-agent)", "10.2307/3003320", "moral hazard and observability"),
    ("R1", "Stigler 1964, A theory of oligopoly (collusion and antitrust)", "10.1086/258853", "theory of oligopoly"),
    ("R1", "Green and Porter 1984, Noncooperative collusion under imperfect price information (collusion and antitrust)", "10.2307/1911462", "noncooperative collusion"),
    ("R1", "Salant, Switzer, Reynolds 1983, Losses from horizontal merger (mergers)", "10.2307/1885620", "losses from horizontal merger"),
    ("R1", "Rochet and Tirole 2003, Platform competition in two-sided markets (antitrust in the new economy)", "10.1162/154247603322493212", "platform competition"),
    ("R1", "Stigler 1971, The theory of economic regulation (regulation and capture)", "10.2307/3003160", "theory of economic regulation"),
    ("R1", "Laffont and Tirole 1991, A theory of regulatory capture (regulation and capture)", "10.2307/2937958", "regulatory capture"),
    ("R1", "Baron and Myerson 1982, Regulating a monopolist with unknown costs (incentive regulation)", "10.2307/1912769", "regulating a monopolist"),
    ("R1", "Laffont and Tirole 1986, Using cost observation to regulate firms (incentive regulation)", "10.1086/261392", "cost observation"),
    ("R1", "Weitzman 1974, Prices vs. quantities (environmental regulation)", "10.2307/2296698", "prices vs"),
    ("R1", "Thaler and Sunstein 2003, Libertarian paternalism (behavioural economics and regulation)", "10.1257/000282803321947001", "libertarian paternalism"),
    ("C7", "Kalman and Bertram 1960, Second method of Lyapunov (stability)", "10.1115/1.3662604", "second method"),
    ("C7", "Sontag 1989, Smooth stabilization implies coprime factorization (input-to-state stability)", "10.1109/9.28018", "smooth stabilization"),
    ("C7", "Dashkovskiy, Ruffer, Wirth 2007, ISS small gain theorem for general networks (stability, small gain)", "10.1007/s00498-007-0014-8", "small gain theorem"),
    ("C7", "Luenberger 1971, An introduction to observers (output feedback and estimation)", "10.1109/tac.1971.1099826", "introduction to observers"),
    ("C7", "Nyquist 1932, Regeneration theory (frequency-domain analysis)", "10.1002/j.1538-7305.1932.tb02344.x", "regeneration theory"),
    ("C7", "Ziegler and Nichols 1942, Optimum settings for automatic controllers (PID)", "10.1115/1.4019264", "optimum settings"),
    ("C7", "Astrom and Hagglund 1984, Automatic tuning of simple regulators (PID)", "10.1016/0005-1098(84)90014-1", "automatic tuning"),
    ("C7", "Zames 1966, Input-output stability, part one: loop gain (small gain, robust performance)", "10.1109/tac.1966.1098316", "input-output stability"),
    ("C7", "Doyle, Glover, Khargonekar, Francis 1989, State-space solutions to H2 and Hinf (robust performance)", "10.1109/9.29425", "state-space solutions"),
    ("C7", "Freudenberg and Looze 1985, Right half plane poles and zeros and design tradeoffs (fundamental limits)", "10.1109/tac.1985.1104004", "right half plane"),
    ("C7", "Robbins and Monro 1951, A stochastic approximation method (stochastic approximation)", "10.1214/aoms/1177729586", "stochastic approximation method"),
    ("C7", "Ljung 1977, Analysis of recursive stochastic algorithms (stochastic approximation, ODE method)", "10.1109/tac.1977.1101561", "recursive stochastic algorithms"),
    ("C7", "Borkar 1997, Stochastic approximation with two time scales (multiple timescales)", "10.1016/s0167-6911(97)90015-3", "two time scales"),
    ("C7", "Chazan and Miranker 1969, Chaotic relaxation (asynchronous schemes)", "10.1016/0024-3795(69)90028-7", "chaotic relaxation"),
    ("R3", "Lessig 1999, The law of the horse: what cyberlaw might teach (technology as regulation)", "10.2307/1342331", "law of the horse"),
    ("R3", "Yeung 2017, Hypernudge: big data as a mode of regulation by design (technology as regulation)", "10.1080/1369118x.2016.1186713", "hypernudge"),
    ("R3", "Matthias 2004, The responsibility gap (liability and torts)", "10.1007/s10676-004-3422-1", "responsibility gap"),
    ("R3", "Solove 2006, A taxonomy of privacy (privacy and human rights)", "10.2307/40041279", "taxonomy of privacy"),
    ("R3", "Szabo 1997, Formalizing and securing relationships on public networks (contract)", "10.5210/fm.v2i9.548", "formalizing and securing"),
    ("R4", "Majone 1994, The rise of the regulatory state in Europe (regulatory state)", "10.1080/01402389408425031", "regulatory state"),
    ("R4", "Carpenter and Moss 2013, Preventing regulatory capture (regulatory politics and capture)", "10.1017/cbo9781139565875", "preventing regulatory capture"),
    ("R4", "Ayres and Braithwaite 1992, Responsive regulation (enforcement, compliance, self-regulation)", "10.1093/oso/9780195070705.001.0001", "responsive regulation"),
    ("R4", "Abbott and Snidal 2000, Hard and soft law in international governance (global regulation)", "10.1162/002081800551280", "hard and soft law"),
    ("R4", "Levi-Faur 2005, The global diffusion of regulatory capitalism (global regulation)", "10.1177/0002716204272371", "regulatory capitalism"),
    ("R4", "Jobin, Ienca, Vayena 2019, The global landscape of AI ethics guidelines (AI governance)", "10.1038/s42256-019-0088-2", "ai ethics guidelines"),
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
    dois = [s[2] for s in SEEDS + ADDED if s[2]]
    batch = [w for i in range(0, len(dois), 50) for w in
             get("works", filter="doi:" + "|".join(dois[i:i + 50]), select=SEL, **{"per-page": 200})["results"]]
    out = []
    for k, (c, lab, doi, frag) in enumerate(SEEDS + ADDED):
        m = [w for w in batch if frag in (w.get("title") or "").lower()]
        exact = [w for w in m if doi and (w.get("doi") or "").lower().endswith(doi.lower())]
        m = exact or m
        w, how = (m[0], "doi") if len(m) == 1 else (None, None)
        if w is None:  # fallback: title search (10 credits); only for misses
            res = get("works", filter="title.search:" + SEARCH[lab], select=SEL, **{"per-page": 5})["results"]
            res = [r for r in res if frag in (r.get("title") or "").lower()]
            w = max(res, key=lambda r: r["cited_by_count"]) if res else None
            how = "title-search"
        out.append({"cluster": c, "label": lab, "doi_tried": doi, "how": how, "group": "run4" if k >= len(SEEDS) else "base",
                    "openalex": sid(w["id"]) if w else None, "oa_title": w["title"] if w else None,
                    "oa_year": w["publication_year"] if w else None, "cited_by": w["cited_by_count"] if w else None})
    json.dump(out, open(os.path.join(D, "seeds.json"), "w"), indent=1)
    return out


if __name__ == "__main__":
    for s in resolve():
        print(s["cluster"], s["how"], s["openalex"], s["oa_year"], s["cited_by"], "|", s["label"], "|", s["oa_title"])
