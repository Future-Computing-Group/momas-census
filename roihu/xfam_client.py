"""Open-weight coding of conference abstracts against codebook v3 (adapted from the PAI-SMS xfam_verify.py client).

Usage (stdlib only, runs on the cluster beside the vLLM server):
  python3 xfam_client.py run   --calls calls.jsonl --results <dir> --base-url URL --model M [--workers 16] [--max-tokens 1024]
  python3 xfam_client.py parse --calls calls.jsonl --results <dir> --out results-parsed.jsonl --failures failures.jsonl

calls.jsonl comes from xfam_inputs.py (one chat request per paper, call_id = opaque xid, per-call JSON schema).
run writes each raw response to <dir>/{call_id}.json before anything parses it, and skips calls whose file exists.
parse validates every raw response against its call's schema (keys, enums, pinned id) and lists the failures.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_one(raw: str, schema: dict) -> tuple[dict | None, str | None]:
    """(record, None) if raw is one JSON object matching the flat schema, else (None, error)."""
    try:
        d = json.loads(raw)
    except (json.JSONDecodeError, TypeError) as e:
        return None, f"invalid json: {e}"
    if not isinstance(d, dict):
        return None, "not an object"
    props = schema["properties"]
    errs = [f"missing {k}" for k in schema["required"] if k not in d]
    errs += [f"unexpected {k}" for k in d if k not in props]
    for k, p in props.items():
        if k not in d:
            continue
        v = d[k]
        if not isinstance(v, str) or ("enum" in p and v not in p["enum"]) or ("const" in p and v != p["const"]):
            errs.append(f"{k}={v!r}")
    return (None, "; ".join(errs)) if errs else (d, None)


def derive(rec: dict) -> dict:
    """OWNERS and FOCUS-na from the three decomposition answers (codebook v3.4); the model's own owners/focus are kept beside."""
    hdm = rec["has_decision_maker"] == "yes"
    owners = "several" if rec["faces_other_parties"] == "yes" else ("one" if hdm else "na")
    return {"owners_derived": owners, "focus_derived": rec["focus"] if hdm else "na"}


def parse(calls, results, out, failures) -> tuple[int, int]:
    ok = bad = 0
    with open(out, "w") as f, open(failures, "w") as g:
        for c in map(json.loads, open(calls)):
            p = Path(results) / f"{c['call_id']}.json"
            if p.exists():
                r = json.loads(p.read_text())
                rec, err = parse_one(r["raw"], c["schema"])
                if err is None and r.get("finish_reason") not in (None, "stop"):
                    rec, err = None, f"finish_reason {r['finish_reason']}"
            else:
                rec, err = None, "no result"
            if rec is None:
                bad += 1
                g.write(json.dumps({"call_id": c["call_id"], "error": err}) + "\n")
            else:
                ok += 1
                if "has_decision_maker" in rec:
                    rec = {**rec, **derive(rec)}
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return ok, bad


def run(a):
    import concurrent.futures as cf
    import time
    import urllib.request
    res = Path(a.results)
    res.mkdir(parents=True, exist_ok=True)
    todo = [c for c in map(json.loads, open(a.calls)) if not (res / f"{c['call_id']}.json").exists()]
    print(f"{len(todo)} calls to run", flush=True)

    def one(c):
        body = {"model": a.model, "messages": c["messages"], "temperature": 0, "seed": 0, "max_tokens": a.max_tokens,
                "response_format": {"type": "json_schema", "json_schema": {"name": "codes", "schema": c["schema"], "strict": True}}}
        err = ""
        for attempt in range(3):
            try:
                req = urllib.request.Request(f"{a.base_url}/chat/completions", json.dumps(body).encode(),
                                             {"Content-Type": "application/json"})
                t = time.time()
                r = json.load(urllib.request.urlopen(req, timeout=600))
                out = {"call_id": c["call_id"], "model": a.model, "raw": r["choices"][0]["message"]["content"],
                       "finish_reason": r["choices"][0].get("finish_reason"), "usage": r.get("usage"),
                       "seconds": round(time.time() - t, 2), "attempt": attempt}
                tmp = res / f".{c['call_id']}.tmp"
                tmp.write_text(json.dumps(out, ensure_ascii=False))
                tmp.rename(res / f"{c['call_id']}.json")  # atomic: a killed job leaves no half-written result to skip
                return c["call_id"], "ok"
            except Exception as e:  # noqa: BLE001 - logged and retried
                err = repr(e)
        return c["call_id"], f"failed: {err}"

    with cf.ThreadPoolExecutor(a.workers) as ex:
        for cid, st in ex.map(one, todo):
            print(cid, st, flush=True)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--calls", required=True)
    r.add_argument("--results", required=True)
    r.add_argument("--base-url", required=True)
    r.add_argument("--model", required=True)
    r.add_argument("--workers", type=int, default=16)
    r.add_argument("--max-tokens", type=int, default=1024)
    p = sub.add_parser("parse")
    p.add_argument("--calls", required=True)
    p.add_argument("--results", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--failures", required=True)
    a = ap.parse_args()
    if a.cmd == "run":
        run(a)
    else:
        print("parsed %d, failed %d" % parse(a.calls, a.results, a.out, a.failures))


if __name__ == "__main__":
    main()
