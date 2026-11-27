"""Build Focus-Check.html: the author codes FOCUS and OWNERS blind on 20 papers, then sees the open-weight screen's codes."""
import json
import re

t = open("template.html").read()
fc = json.load(open("../data/xfam/focus-check-20.json"))
items = {json.loads(l)["xid"]: json.loads(l) for l in open("../data/xfam/items-full.jsonl")}
by_sample = {v["sample_id"]: k for k, v in items.items() if v.get("sample_id")}
full = {}
for line in open("../data/xfam/full-v34/results-parsed.jsonl"):
    r = json.loads(line)
    full[r["id"]] = r
data = {"practice": [], "validation": []}
for x in fc:
    m = full[by_sample[x["id"]]]
    data["validation"].append({"id": x["id"], "title": x["title"], "abstract": x["abstract"],
                               "c": {"focus": m["focus_derived"], "owners": m["owners_derived"], "conf": None,
                                     "note": m.get("faces_quote") or m.get("quote") or "no phrase quoted",
                                     "note2": f"experiments run by: {m['eval_run']}; interests: {m['interests']}"}})
R = [
    (r"<title>Principal Census Check</title>", "<title>Focus Check</title>"),
    (r"<h1>Principal census check</h1>", "<h1>Focus check</h1>"),
    (r'const FIELDS = \[.*?\]\]\]\];', 'const FIELDS = [\n  ["focus","Focus","what the contribution is about",[["agent","Agent"],["interaction","Interaction"],["na","No decision-maker"]]],\n  ["owners","Owners","the setting the method is for",[["one","One"],["several","Several"],["na","Not fixed"]]]];'),
    (r'<dl class="defs">.*?</dl>', '<dl class="defs"><dt>Focus</dt><dd>Agent: the contribution improves or analyses the performance, decisions or internals of one agent or one team, treating the other parties as its environment (wins more, negotiates better, best-responds). Interaction: the contribution concerns the joint outcome or the rules between the parties (efficiency, welfare, fairness across parties, equilibrium properties, collusion, incentive compatibility, mechanism, market, protocol or institution design, governance). A learning-agents paper whose analysis is the outcome they reach together is interaction. One developer training one model is agent. No decision-maker only if the paper has no learner, model or analyst at all.</dd><dt>Owners</dt><dd>The setting the method is meant for, even if the experiments simulate it. Several if the agents are built to face decision-makers that other parties own or that act for themselves (other organizations\' or users\' agents, humans, bidders, applicants, voters, firms, self-interested agents whose incentives a designer sets, an attacker). Otherwise one if one party trains, runs or deploys every decision-maker (a single model, a team built by one developer, self-play producing one policy, equilibrium computation as analysis). Otherwise not fixed.</dd></dl>', ),
    (r"The 51 papers", "The 20 papers"),
    (r'Fifty-one accepted papers from NeurIPS, ICML and ACM EC, in random order, with no venue or year shown\. Pick one option in each of the four rows', 'Twenty accepted papers from NeurIPS, ICML and ACM EC, in random order, with no venue or year shown. Pick one option in each of the two rows'),
    (r"Where the coders coded a paper differently", "Where the open-weight screen coded a paper differently"),
    (r"About 25 minutes\.", "About 10 minutes."),
    (r'"Five practice papers first"', '"The 20 papers"'),
    (r'These are not part of the check\. They let you settle into the four rows and the definitions \(open them with \? or the Definitions button; they are the coders\' codebook\)\.', 'Twenty accepted papers, no venue or year shown. Code Focus and Owners from title and abstract (definitions under ? or the Definitions button); afterwards you see the open-weight screen\'s codes where they differ.'),
    (r"Where the coders differed", "Where the screen differed"),
    (r" · coders: ", " · screen: "),
    (r"I would change to the coders'", "I would change to the screen's"),
    (r"Coder's justification", "Screen's deciding phrase"),
    (r"Second coder: ", "Screen: "),
    (r"compare them with the coders'", "compare them with the screen"),
    (r'"principal-check"', '"focus-check"'),
]
for a, b in R:
    t, n = re.subn(a, lambda _m: b, t, flags=re.S)
    assert n >= 1, a[:50]
open("Focus-Check.html", "w").write(t.replace("__DATA__", json.dumps(data, ensure_ascii=False)))
print(len(data["validation"]))
