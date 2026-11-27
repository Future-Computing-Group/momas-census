"""The author's blind check: 20 papers from the 2025 agent and LLM-agent keyword strata, 20 from the random strata, 10 EC papers (seed 50)."""
import csv
import json
import random

items = json.load(open("data/stage2-items.json"))
rng = random.Random(50)
pick = lambda f, n: rng.sample([x for x in items if f(x)], n)
a = pick(lambda x: x["venue"].endswith("2025") and ("agent" in x["strata"] or "llm_agent" in x["strata"]), 20)
r = pick(lambda x: "random" in x["strata"] and x not in a, 20)
c = pick(lambda x: "control" in x["strata"], 10)
sel = a + r + c
rng.shuffle(sel)
if __name__ == "__main__":
    have = [row["id"] for row in csv.DictReader(open("data/pi-validation-50.csv"))]
    assert have == [x["id"] for x in sel], "draw does not reproduce data/pi-validation-50.csv"
    print("reproduces", len(sel), "ids")
