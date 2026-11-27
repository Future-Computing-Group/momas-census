import hashlib
import json
from pathlib import Path

import pytest

import deploy_layers as dl

NONE = [{"party_kind": "none", "action": "none", "quote": ""}]


def rec(i, layers, persons="no", live="yes", status="ok"):
    return {"id": i, "status": status, "live_agent": live, "other_owner_layers": layers, "outside_persons": persons, "confidence": "high"}


def test_supplier_portal_order_is_third_party_reach():
    d = dl.derive(rec("a", [{"party_kind": "counterparty-org", "action": "transacts", "quote": "places the order in the supplier portal"}]))
    assert d["acts_on_other_owner"] and d["third_party_reach"]
    assert not d["model_vendor_reach"] and not d["platform_vendor_reach"] and not d["agent_to_agent"]


def test_vendor_platform_writing_vendor_hosted_crm_is_platform_vendor_reach_only():
    d = dl.derive(rec("b", [{"party_kind": "platform-vendor", "action": "runs-on", "quote": "built on Agentforce"}, {"party_kind": "platform-vendor", "action": "writes", "quote": "updates the case in Service Cloud"}]))
    assert d["acts_on_other_owner"] and d["platform_vendor_reach"]
    assert not d["third_party_reach"] and not d["model_vendor_reach"]


def test_model_vendor_is_reported_apart_from_platform_vendor():
    d = dl.derive(rec("c", [{"party_kind": "model-vendor", "action": "runs-on", "quote": "powered by GPT-4o"}]))
    assert d["model_vendor_reach"] and not d["platform_vendor_reach"] and d["acts_on_other_owner"]


def test_chat_reply_to_customer_is_counterparty_not_reach():
    d = dl.derive(rec("d", NONE, persons="yes"))
    assert d["counterparty"] and not d["acts_on_other_owner"] and not d["third_party_reach"]


def test_reading_a_public_page_gives_nothing():
    d = dl.derive(rec("e", NONE))
    assert not any(d.values())


def test_other_org_agent_is_a2a_and_third_party():
    d = dl.derive(rec("f", [{"party_kind": "other-org-agent", "action": "messages-agent", "quote": "negotiates with the carrier's agent"}]))
    assert d["agent_to_agent"] and d["third_party_reach"] and d["acts_on_other_owner"]


def test_validate_rejects_bad_codes():
    assert dl.validate(rec("a", NONE)) == []
    assert dl.validate(rec("a", [{"party_kind": "vendor", "action": "writes", "quote": "x"}]))
    assert dl.validate(rec("a", [{"party_kind": "none", "action": "none", "quote": ""}, {"party_kind": "tool-operator", "action": "calls-tool", "quote": "x"}]))
    assert dl.validate(rec("a", [], live="yes"))  # a live agent needs at least the none entry
    assert dl.validate(rec("a", [], persons="na", live="no")) == []
    assert dl.validate(rec("a", [{"party_kind": "tool-operator", "action": "calls-tool", "quote": ""}]))  # quote required


def test_derive_not_live_is_none():
    assert dl.derive(rec("g", [], persons="na", live="no")) is None


def test_estimate_both_either_and_kappa():
    lay = lambda k: [{"party_kind": k, "action": "writes", "quote": "q"}] if k != "none" else NONE
    c1 = {"p1": rec("p1", lay("tool-operator")), "p2": rec("p2", lay("none")), "p3": rec("p3", lay("tool-operator")), "p4": rec("p4", [], persons="na", live="no")}
    c2 = {"p1": rec("p1", lay("tool-operator")), "p2": rec("p2", lay("tool-operator")), "p3": rec("p3", [], persons="na", live="no"), "p4": rec("p4", lay("none"))}
    e = dl.estimate(c1, c2)
    t = "third_party_reach"
    assert (e["c1"][t]["k"], e["c1"][t]["n"]) == (2, 3) and (e["c2"][t]["k"], e["c2"][t]["n"]) == (2, 3)
    assert (e["both"][t]["k"], e["both"][t]["n"]) == (1, 2)  # p1, p2 live for both; only p1 coded by both
    assert (e["either"][t]["k"], e["either"][t]["n"]) == (3, 4)  # p1, p2, p3 reach on some live reading; all four live for someone
    assert e["kappa"][t]["n"] == 2 and e["kappa"][t]["agree"] == 1
    assert e["gate"]["kappa"]["n"] == 4 and e["gate"]["c1"] == 3 and e["gate"]["both"] == 2 and e["gate"]["either"] == 4
    assert 0 <= e["both"][t]["lo"] <= e["both"][t]["share"] <= e["both"][t]["hi"] <= 1
    assert set(e["kappa"]) == set(dl.DERIVED)


def test_estimate_requires_same_pages():
    with pytest.raises(AssertionError):
        dl.estimate({"a": rec("a", NONE)}, {"b": rec("b", NONE)})


def test_fragments_from_estimate():
    m = lambda k, n: {"k": k, "n": n, "share": k / n, "lo": 0.01, "hi": 0.2}
    est = {v: {f: m(3, 80) for f in dl.DERIVED} for v in ("c1", "c2", "both", "either")}
    est["kappa"] = {f: {"n": 78, "agree": 75, "kappa": 0.81} for f in dl.DERIVED}
    est["gate"] = {"c1": 80, "c2": 80, "both": 78, "either": 82, "kappa": {"n": 93, "agree": 90, "kappa": 0.9}}
    fr = dl.fragments(est)
    assert set(fr) == {"deploy-layers-short.tex", "tab-deploy-layers.tex", "deploy-any-layer.tex", "deploy-platform.tex", "deploy-a2a.tex", "deploy-third.tex", "deploy-model.tex", "deploy-tool.tex", "deploy-counterparty.tex", "deploy-gate-agreement.tex"}
    assert fr["deploy-any-layer.tex"] == fr["deploy-platform.tex"] == fr["deploy-a2a.tex"] == "3 of 80"
    assert fr["deploy-third.tex"] == "3 of 80 (3.8\\%, 1.0 to 20.0\\%)"
    assert "3 of 80 (3.8\\%)" in fr["deploy-layers-short.tex"]
    rows = fr["tab-deploy-layers.tex"].strip().splitlines()
    assert len(rows) == len(dl.DERIVED) and all(r.endswith("\\\\") and "0.81" in r for r in rows)


# the files the layers pass reads from; the earlier deployment codes stay byte-identical
FROZEN = {
    "codebook-deploy.md": "2827f78d4177b8b07e8af08c5c26da8b4df8bd0090058ff1bf1738f984b2c110",
    "codebook-deploy-roleindep.md": "7fc8e2579633cef8ce9d766e76da8a7ed916ea183ed6608723c10357b26d53a9",
    "data/coded/deploy-00.jsonl": "15be741974ba6cfac90b02cc7435d3779fd4cde1d3bbe94997fd4ab75e2dff0f",
    "data/coded/deploy-01.jsonl": "cae47616ec2c25f754684c3db1adc3b0a0cf72d2b99e72576e68e02b794c4e31",
    "data/coded/deploy-02.jsonl": "5654d20910456b5e0d2740c9a68c1dbc424427155db0cd3f6f1030f7b5af8ddc",
    "data/coded/deploy-03.jsonl": "a62016717759e86a6374ae99ff264f488d6d91276cc87787af9e384ee085faee",
    "data/coded/deploy-04.jsonl": "09cd6a83a0d193d0c3e9461b436387ac64b820f313d83b4ce743f3556c71d59d",
    "data/coded/deploy-05.jsonl": "8c326eaf36eb4ae97ed9104a6361770ed57e703e8e7eac760491ad471ff5dc29",
    "data/coded/deploy-overlap-00.jsonl": "71b9a0c6cc1189f0a822edd4cc015054120c467f7d08bdc94beb4601cdeff7df",
    "data/coded/deploy-overlap-01.jsonl": "6ed893b5083c89d44d79ab0989b7047cd8b3c2a1d2aef30002d8a588da161820",
    "data/coded/deploy-second-00.jsonl": "1e001958032e4ceb14b69929a915d71a9b3e916eb8668cc4af0b30020accb0a3",
    "data/coded/deploy-second-01.jsonl": "1c8f07b51612a760e026be5a59ecd686f27709ba3f088a21bb54c5230f777102",
    "data/coded/deploy-second-02.jsonl": "9f74bc8151a034c98f0a8620a5b54994ad6da43677c597b017b3167909545224",
    "data/coded/deploy-second-03.jsonl": "1556ebba9561b0a81e27c9e25073d9062162af56be00cedfe91a8f7b3b127e92",
    "data/coded/deploy-second-04.jsonl": "6a0960eb0e7c75abbcb491465ad835b7e46d8d9643eaa2ac0fff2caf107acabf",
    "data/coded/deploy-second-05.jsonl": "aee8f6cbb8da7dd48e8399b5d42da82cd02e03cb748c460bc83480136ea0bd28",
    "data/coded/r2-deploy-01.jsonl": "5c0988308d62697455b4cfac6b95fa9dad58d52399272489e11633d0eeca6610",
    "data/coded/r2-deploy-02.jsonl": "194f5c73f832fc04eb3f634a721e193dc7b3895e51ee444dec79aaf322ecf19c",
    "data/coded/r2-deploy-03.jsonl": "15cbddb554d35a53182062577fbb84bf3a4f4cd709cee56f0235c3c2e92d153e",
    "data/coded/r2-deploy-04.jsonl": "89a95332f20a6071406b9d976013fc5d84bd7f0943f55a28be4e2e0a74475251",
}


def test_earlier_deployment_codes_unchanged():
    for p, h in FROZEN.items():
        assert hashlib.sha256(Path(p).read_bytes()).hexdigest() == h, p


def test_frame_is_the_set_to_recode():
    f = dl.frame()
    assert len(f) == len(set(f)) == 93 and len(f) <= 99
    assert {"d001", "d013", "d024", "d114", "d145", "d153"} <= set(f)  # readable Google Cloud pages coded blocked in v2
    assert {"d010", "d044", "d108", "d035"} <= set(f)  # AGENT disagreements coded no in v2; live agent without a stated reach


snap = pytest.mark.skipif(not Path("data/raw/deploy-pages").is_dir(), reason="page snapshots are local only")


@snap
def test_jobs_blind_batches_and_briefs(tmp_path):
    out = dl.jobs(tmp_path)
    names = sorted(out)
    assert names == [f"{n:02d}" for n in range(1, 6)]
    seen = []
    for b in names:
        items = json.load(open(tmp_path / f"layers-{b}.json"))
        assert all(set(x) == {"id", "text"} and x["text"].strip() for x in items)
        seen += [x["id"] for x in items]
    assert sorted(seen) == sorted(dl.frame())
    briefs = [json.loads(l) for l in open(tmp_path / "layers-briefs.jsonl")]
    assert len(briefs) == 10 and len({b["private"] for b in briefs}) == 10
    for b in briefs:
        t = b["brief"]
        assert 'BASE = "BASE"' in t and "BASE/codebook-deploy-layers.md" in t and f"BASE/data/batches/layers-{b['batch']}.json" in t
        assert f"BASE/data/coded/layers-{b['batch']}-{b['coder']}.jsonl" in t and b["private"] in t and b["private"].startswith("/private/tmp/")
        assert b["writes"] == [f"layers-{b['batch']}-{b['coder']}.jsonl"]


def test_tool_operator_and_counterparty_org_are_reported_apart():
    d = dl.derive(rec("h", [{"party_kind": "tool-operator", "action": "calls-tool", "quote": "files the ticket in ServiceNow"}]))
    assert d["tool_operator_reach"] and not d["counterparty_reach"] and d["third_party_reach"]
    d = dl.derive(rec("i", [{"party_kind": "counterparty-org", "action": "transacts", "quote": "places the order in the supplier portal"}]))
    assert d["counterparty_reach"] and not d["tool_operator_reach"]
    assert {"tool_operator_reach", "counterparty_reach"} <= set(dl.DERIVED)


def test_model_tool_and_counterparty_fragments():
    m = lambda k, n: {"k": k, "n": n, "share": k / n, "lo": 0.01, "hi": 0.2}
    est = {v: {f: m(3, 80) for f in dl.DERIVED} for v in ("c1", "c2", "both", "either")}
    est["both"]["model_vendor_reach"] = m(17, 83)
    est["kappa"] = {f: {"n": 78, "agree": 75, "kappa": 0.81} for f in dl.DERIVED}
    est["gate"] = {"kappa": {"n": 93, "agree": 88, "kappa": 0.64}}
    fr = dl.fragments(est)
    assert fr["deploy-model.tex"] == "17 of 83"
    assert fr["deploy-tool.tex"] == fr["deploy-counterparty.tex"] == "3 of 80 (3.8\\%, 1.0 to 20.0\\%)"


def test_committed_layer_estimates_keep_their_values():
    import subprocess
    head = json.loads(subprocess.run(["git", "show", "HEAD:data/estimates-deploy-layers.json"], capture_output=True, text=True, check=True).stdout)
    cur = json.load(open("data/estimates-deploy-layers.json"))
    for v in ("c1", "c2", "both", "either", "kappa"):
        assert {f: cur[v][f] for f in head[v]} == head[v], v
    assert cur["gate"] == head["gate"] and cur["pages"] == head["pages"]
    assert cur["both"]["tool_operator_reach"]["n"] == cur["both"]["acts_on_other_owner"]["n"]


def test_table_names_the_further_party_row_as_the_text_does():
    m = lambda k, n: {"k": k, "n": n, "share": k / n, "lo": 0.01, "hi": 0.2}
    est = {v: {f: m(3, 80) for f in dl.DERIVED} for v in ("c1", "c2", "both", "either")}
    est["kappa"] = {f: {"n": 78, "agree": 75, "kappa": 0.81} for f in dl.DERIVED}
    est["gate"] = {"c1": 80, "c2": 80, "both": 78, "either": 82, "kappa": {"n": 93, "agree": 90, "kappa": 0.9}}
    tab = dl.fragments(est)["tab-deploy-layers.tex"]
    assert "further party (tool operator" in tab and "third party" not in tab


def test_fragments_print_an_undefined_kappa_as_a_dash_and_the_gate_agreement():
    m = lambda k, n: {"k": k, "n": n, "share": k / n, "lo": 0.01, "hi": 0.2}
    est = {v: {f: m(3, 80) for f in dl.DERIVED} for v in ("c1", "c2", "both", "either")}
    est["kappa"] = {f: {"n": 78, "agree": 75, "kappa": 0.81} for f in dl.DERIVED}
    est["kappa"]["agent_to_agent"] = {"n": 78, "agree": 78, "kappa": None}
    est["gate"] = {"c1": 80, "c2": 80, "both": 78, "either": 82, "kappa": {"n": 93, "agree": 88, "kappa": 0.6387}}
    fr = dl.fragments(est)
    row = [r for r in fr["tab-deploy-layers.tex"].splitlines() if r.startswith(dl.LABEL["agent_to_agent"])][0]
    assert row.endswith("& -- \\\\")
    assert fr["deploy-gate-agreement.tex"] == "88 of 93 pages ($\\kappa = 0.64$)"


def test_estimate_stores_an_undefined_kappa_as_none():
    c = {i: rec(i, NONE) for i in "abc"}
    e = dl.estimate(c, c)
    assert e["kappa"]["agent_to_agent"]["kappa"] is None


def test_frame_reads_the_page_manifest_not_the_snapshots(monkeypatch, tmp_path):
    want = dl.frame()
    monkeypatch.setattr(dl, "SNAP", tmp_path / "no-snapshots")  # a clean clone has no data/raw/deploy-pages/
    assert dl.frame() == want


def test_page_manifest_hashes_every_fetched_snapshot():
    m = json.load(open("data/deploy-pages-manifest.json"))
    fetched = [r for r in m.values() if "error" not in r]
    assert len(fetched) == 150 and all(len(r["sha256"]) == 64 and len(r["txt_sha256"]) == 64 for r in fetched)


def test_fetcher_refuses_to_overwrite(tmp_path):
    import fetch_deploy_pages as f
    (tmp_path / "d000.txt").write_text("old")
    with pytest.raises(FileExistsError):
        f.save(tmp_path, "d000", b"<p>new</p>")
    assert (tmp_path / "d000.txt").read_text() == "old"
    rec = f.save(tmp_path, "d001", b"<p>new</p>")
    assert rec["sha256"] == hashlib.sha256(b"<p>new</p>").hexdigest() and rec["txt_sha256"] == hashlib.sha256(b"new").hexdigest()
