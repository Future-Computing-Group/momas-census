"""OpenAlex client: cached GET, no mailto/email/api_key ever sent. Stdlib only."""
import hashlib, json, os, time, urllib.parse, urllib.request, urllib.error

BASE = "https://api.openalex.org"
RAW = os.path.join(os.path.dirname(os.path.abspath(__file__)), "raw")
os.makedirs(RAW, exist_ok=True)
CALLS = {"net": 0, "cache": 0}


def get(path, **params):
    q = urllib.parse.urlencode(params, safe=":|,")
    url = f"{BASE}/{path}?{q}"
    assert "mailto" not in url and "@" not in url and "api_key" not in url
    fn = os.path.join(RAW, hashlib.sha1(url.encode()).hexdigest() + ".json")
    if os.path.exists(fn):
        CALLS["cache"] += 1
        return json.load(open(fn))["response"]
    time.sleep(0.2)
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "fcg-biblio"}), timeout=60) as r:
            body = json.load(r)
            rem = r.headers.get("x-ratelimit-remaining")
    except urllib.error.HTTPError as e:
        raise SystemExit(f"HTTP {e.code} on {url}: {e.read()[:300]}")
    CALLS["net"] += 1
    json.dump({"url": url, "response": body}, open(fn, "w"))
    if rem is not None and int(rem) < 60:
        raise SystemExit(f"credit floor reached (remaining {rem}); rerun later, cache keeps progress")
    return body


def get_all(path, **params):
    """Page-number paging (cursor paging needs an API key, which we do not use); OpenAlex caps this at 10,000 results."""
    out, page = [], 1
    while True:
        d = get(path, page=page, **{"per-page": 200}, **params)
        out += d["results"]
        if not d["results"] or len(out) >= d["meta"]["count"]:
            break
        assert page * 200 < 10000, "result set exceeds the 10k page-paging cap"
        page += 1
    return out


def sid(x):
    return x.rsplit("/", 1)[-1] if x else None
