import os

import pytest

FILES = ("data/xfam/stage2-part-e.json", "data/xfam/stage2-parts-fg.json", "data/xfam/stage2-part-ec.json")
DATA = all(os.path.exists(p) for p in ("data/xfam/full-v34/results-parsed.jsonl", "data/xfam/items-full.jsonl", "data/xfam/stage2-confirm.json"))


def test_parts_on_synthetic_rows():
    from draw_stage2_parts import part_e, parts_fg, part_ec
    rows = [{"id": f"x{n:03d}", "agent": "no" if n < 60 else "yes", "llm_basis": "yes" if n >= 60 else "no",
             "owners_derived": "several" if n % 10 == 0 else "one", "interests": "one" if n % 20 == 0 else "several-aligned"} for n in range(100)]
    items = {r["id"]: {"venue": "ec-2025" if int(r["id"][1:]) >= 95 else "neurips-2025"} for r in rows}
    assert part_e(rows) == [f"x{n:03d}" for n in range(0, 100, 20)]
    fg = parts_fg(rows, items, confirmed={"x001"}, n_f=5, n_g=3)
    assert len(fg["f"]) == 5 and fg["f"] == sorted(fg["f"]) and "x001" not in fg["f"] and all(int(i[1:]) < 60 and int(i[1:]) % 10 for i in fg["f"])
    assert len(fg["g"]) == 3 and all(60 <= int(i[1:]) and items[i]["venue"] == "neurips-2025" for i in fg["g"])
    done = {"x001"} | set(part_e(rows)) | set(fg["f"]) | set(fg["g"])
    assert part_ec(items, done) == sorted(i for i in items if items[i]["venue"] == "ec-2025" and i not in done)


@pytest.mark.skipif(not DATA, reason="needs the local full-run files")
def test_draw_reproduces_the_stored_parts_byte_for_byte(tmp_path):
    from draw_stage2_parts import write
    write(tmp_path)
    for p in FILES:
        assert (tmp_path / os.path.basename(p)).read_bytes() == open(p, "rb").read(), p
