#!/usr/bin/env python3
"""check_publishing.py — every emitter has a publishing row, and every KDE Store id it cites exists.

⚑ THE CLAIM.  catalog/publishing.md is a table of where each emission goes.
Two things about it can be measured here; the rest (the upload form, whether
generated themes are welcome) is tagged [MEM]/[ABS] in the table and is not
claimed. (1) Every emitter — everything emitters.ORDER runs, plus the
render_all() emitters make_deb drives directly — has at least one row, so a
new target cannot ship without a stated route. (2) Every `id N` the table
cites for the KDE Store is a category in the OCS listing cached at
catalog/ocs-categories.xml, so a number does not outlive the store's
taxonomy unnoticed. `--refresh` re-fetches the listing (SKIP offline: the
cached file is the measurement, dated).

    scripts/check_publishing.py                  # the verdict, as opa_gate publishing decides it
    scripts/check_publishing.py --json           # the measurement policy/publishing.rego decides
    scripts/check_publishing.py --rows           # emitter -> venue, as the table says
    scripts/check_publishing.py --categories [substr]   # the OCS categories (filtered)
    scripts/check_publishing.py --refresh        # re-fetch the OCS listing into the cache
    scripts/check_publishing.py --selftest

WEAKNESS. A cited id that EXISTS is not a cited id that is RIGHT for the
artifact; the display name is printed beside each so a reader can judge, and
the choice between 114 and 717 is [MEM] until someone uploads.
"""
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TABLE = os.path.join(ROOT, "catalog", "publishing.md")
CACHE = os.path.join(ROOT, "catalog", "ocs-categories.xml")
OCS_URL = "https://api.kde-look.org/ocs/v1/content/categories"

# render_all() emitters make_deb drives that are not in emitters.ORDER
DIRECT = ("make_plymouth", "make_wallpaper_live", "make_notify_marquee", "make_kvantum")


def categories(path=CACHE):
    """{id: (name, display_name, xdg_type)} from the cached OCS listing, or None."""
    if not os.path.isfile(path):
        return None
    root = ET.parse(path).getroot()
    out = {}
    for cat in root.iter("category"):
        cid = (cat.findtext("id") or "").strip()
        if cid:
            out[cid] = ((cat.findtext("name") or "").strip(),
                        (cat.findtext("display_name") or "").strip(),
                        (cat.findtext("xdg_type") or "").strip())
    return out


def rows(path=TABLE):
    """[(emitter, venue, route)] from the table's first three columns."""
    out = []
    for line in open(path, encoding="utf-8"):
        if not line.startswith("|") or line.startswith("|---") or line.startswith("| emitter"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 4:
            out.append((cells[0].strip("`"), cells[2], cells[3]))
    return out


def emitters():
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    import emitters as E
    names = [m for m, _w in E.ORDER] + list(DIRECT)
    return sorted(set(names) - {"make_preview"})        # preview is an input to others, not a target


def cited_ids(route):
    return re.findall(r"\bid (\d+)", route)


def measure(table_rows, cats, emitter_names):
    """The MEASUREMENT policy/publishing.rego decides (W50). Facts only: the
    emitter population (`cases`, each with how many table rows name it), every
    table row (its emitter key, venue, the ids its route cites and whether each
    is in the cached listing, and whether the route carries a '?'), and whether
    the listing was present at all. Which venue must cite real ids, and that an
    uncovered emitter or a guessed id is a defect, is the policy's ruling."""
    keys = [r[0].split(" ")[0] for r in table_rows]
    return {
        "listing": cats is not None,
        "cases": [{"emitter": e, "rows": keys.count(e)} for e in emitter_names],
        "rows": [{"emitter": e, "venue": v, "route": r, "guessed": "?" in r,
                  "ids": [{"id": cid, "listed": cats is not None and cid in cats}
                          for cid in cited_ids(r)]}
                 for e, v, r in table_rows],
    }


def main(argv):
    known = {"--rows", "--categories", "--refresh", "--json"}
    args = [a for a in argv[1:] if a.startswith("--")]
    rest = [a for a in argv[1:] if not a.startswith("--")]
    for a in args:
        if a not in known:
            print(f"check_publishing: unknown flag {a!r}", file=sys.stderr)
            return 2
    if "--refresh" in args:
        import urllib.request
        try:
            data = urllib.request.urlopen(OCS_URL, timeout=30).read()
        except Exception as e:                            # noqa: BLE001
            print(f"check_publishing: SKIP refresh — offline or refused ({type(e).__name__}); "
                  f"the cached listing stands", file=sys.stderr)
            return 0
        open(CACHE, "wb").write(data)
        print(f"check_publishing: cached {len(categories())} categories from {OCS_URL}")
        return 0
    if "--categories" in args:
        cats = categories()
        if cats is None:
            print("check_publishing: no cached listing; --refresh first", file=sys.stderr)
            return 2
        sub = rest[0].lower() if rest else ""
        shown = 0
        for cid, (name, disp, xdg) in sorted(cats.items(), key=lambda kv: int(kv[0])):
            if sub in name.lower() or sub in disp.lower() or sub in xdg.lower():
                shown += 1
                print(f"{cid:>4}  {disp:40} {name:36} {xdg}")
        print(f"{shown} of {len(cats)} categories match {sub!r}")
        return 0
    table_rows = rows()
    if "--rows" in args:
        for e, v, r in table_rows:
            print(f"{e:22} {v:28} {r}")
        return 0
    if "--json" in args:
        print(json.dumps(measure(table_rows, categories(), emitters()), indent=1))
        return 0
    import opa_gate
    return opa_gate.gate("publishing")


def _selftest():
    ok = True

    def chk(label, got, want):
        nonlocal ok
        if got != want:
            print(f"  FAIL {label}: got {got!r} want {want!r}")
            ok = False
        else:
            print(f"  ok   {label}")

    # ⚑ THE MEASUREMENT CAN SEE (W50). Whether what it sees is a defect is
    # policy/publishing.rego's ruling, refused and admitted in publishing_test.rego.
    cats = {"112": ("x", "Plasma Color Schemes", "plasma_color_schemes"), "722": ("y", "Global Themes", "")}
    good = [("make_schemes", "KDE Store", "id 112 [OCS]"), ("make_deb", "KDE Store", "id 722"),
            ("make_css", "the operator's site", "direct")]
    m = measure(good, cats, ["make_schemes", "make_deb", "make_css", "make_new"])
    chk("an emitter without a row is seen (0 rows)", m["cases"][-1], {"emitter": "make_new", "rows": 0})
    chk("a covered emitter is seen", m["cases"][0], {"emitter": "make_schemes", "rows": 1})
    m = measure(good + [("make_x", "KDE Store", "id 999"), ("make_y", "KDE Store", "id 723?")], cats, ["make_x"])
    chk("an id not in the listing is seen", m["rows"][3]["ids"], [{"id": "999", "listed": False}])
    chk("a listed id is seen", m["rows"][0]["ids"], [{"id": "112", "listed": True}])
    chk("a guessed id (?) is seen", m["rows"][4]["guessed"], True)
    chk("no cached listing is seen", measure(good, None, ["make_schemes"])["listing"], False)
    chk("cited_ids reads several", cited_ids("id 114 or id 717"), ["114", "717"])
    real = categories()
    chk("the cached listing parses to many categories", real is not None and len(real) > 100, True)
    print("check_publishing selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
