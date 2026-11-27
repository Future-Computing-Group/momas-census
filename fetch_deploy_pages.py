"""Snapshot every deployment case page (HTML and extracted text) under data/raw/deploy-pages/, with a SHA-256 manifest
(data/deploy-pages-manifest.json: URL, fetch time, sha256 of the HTML and of the text). Refuses to overwrite an existing snapshot
or manifest: move them aside to re-fetch, then compare the new hashes with the released manifest (vendor pages change)."""
import datetime
import hashlib
import json
import re
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

OUT = Path("data/raw/deploy-pages")
MANIFEST = Path("data/deploy-pages-manifest.json")
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"


class Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.out, self.skip = [], 0

    def handle_starttag(self, tag, attrs):
        self.skip += tag in ("script", "style", "noscript", "svg")

    def handle_endtag(self, tag):
        self.skip -= tag in ("script", "style", "noscript", "svg") and self.skip > 0

    def handle_data(self, d):
        if not self.skip and d.strip():
            self.out.append(d.strip())


def text(html):
    p = Text()
    p.feed(html)
    return re.sub(r"\s+", " ", " ".join(p.out))


def save(out, i, raw):
    """Write the HTML and text snapshot of page i (FileExistsError if either exists) and return their hashes."""
    t = text(raw.decode("utf-8", "replace")).encode()
    if (Path(out) / f"{i}.txt").exists():
        raise FileExistsError(Path(out) / f"{i}.txt")
    with open(Path(out) / f"{i}.html", "xb") as f:
        f.write(raw)
    with open(Path(out) / f"{i}.txt", "xb") as f:
        f.write(t)
    return {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw), "text_chars": len(t.decode()), "txt_sha256": hashlib.sha256(t).hexdigest()}


if __name__ == "__main__":
    if MANIFEST.exists():
        raise SystemExit(f"{MANIFEST} exists: refusing to overwrite the released manifest")
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = {}
    for it in json.load(open("data/deploy-items.json")):
        rec = {"url": it["url"], "fetched": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")}
        try:
            raw = urllib.request.urlopen(urllib.request.Request(it["url"], headers={"User-Agent": UA}), timeout=20).read()
        except Exception as e:  # recorded, not fatal: some vendor pages block scripted fetches
            rec["error"] = f"{type(e).__name__}: {e}"[:200]
        else:
            rec.update(save(OUT, it["id"], raw))
        manifest[it["id"]] = rec
        print(it["id"], rec.get("text_chars", rec.get("error")), flush=True)
    with open(MANIFEST, "x") as f:
        json.dump(manifest, f, indent=1)
