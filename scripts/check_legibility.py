#!/usr/bin/env python3
"""check_legibility.py — can a machine READ what the aperture field shows? (W56)

Operator, 2026-09-22: "OCR models might be useful for helping optimize how we do
our supersampling alignment." The round trip: render a string through the
aperture field (render_qml aperture-text; the probe's font / text / rows /
gamma / offsetRows are holes make_notify_marquee fills), LOW-PASS at the pitch
(what the eye does at distance — raw pips defeat OCR: tesseract read nothing
until a Gaussian at ~1.5 pitch reconnected the strokes, measured s117),
threshold, tesseract, and the normalised Levenshtein similarity to the source
string. Legibility becomes a NUMBER; then it is an objective (--sweep) over the
alignment's parameters. policy/legibility.rego decides.

    scripts/check_legibility.py             # every case, its OCR read and its score
    scripts/check_legibility.py --json      # the measurement
    scripts/check_legibility.py --sweep     # γ x blur over the Latin case: the best alignment
    scripts/check_legibility.py --selftest  # the scorer and the pre-processing can see

WEAKNESS: tesseract is a reader of PRINT — a dot matrix is not its training
distribution, so the score is a floor on legibility, not a measure of it; the
low-pass radius is itself a parameter (the sweep owns it); a language without
tessdata is WITHHELD (eng / enm / osd here — chi_sim / jpn are the operator's);
the score is character-level, so a dropped space costs as much as a dropped
letter.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

# (label, font, text, lang, rows, offset_rows): what is rendered and which tessdata reads it
CASES = (
    ("latin-unifont-1to1", "Unifont", "Hello world 42", "eng", 16, 6),
    ("latin-unifont-2to1", "Unifont", "Hello world 42", "eng", 8, 0),
    ("latin-liberation", "Liberation Mono", "Hello world 42", "eng", 8, 0),
    ("cjk-unifont-1to1", "Unifont", "世界", "chi_sim", 16, 4),
)
PITCH_PX = 4          # the probe's pitch (u: 4)
# ⚑ MEASURED (s131, --sweep): 1.0 pitch beats 1.5 on every case (1:1 0.786 vs 0.714;
# 2:1 at γ 0.5 1.000 vs 0.714); at 2.0 the strokes merge and reads collapse.
LOWPASS_PITCHES = 1.0
UPSCALE = 4


def levenshtein(a, b):
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def similarity(source, read):
    """1 - normalised edit distance, over the source's length; whitespace collapsed."""
    s, r = " ".join(source.split()), " ".join(read.split())
    if not s:
        return 0.0
    return max(0.0, 1.0 - levenshtein(s, r) / max(len(s), len(r), 1))


TESSERACT = shutil.which("tesseract") or ("/usr/bin/tesseract" if os.path.isfile("/usr/bin/tesseract") else None)


def languages():
    """tesseract's installed languages, or None without tesseract. The gate's
    environment may carry a PATH without /usr/bin (measured s131: four withheld
    under paperkit, one alone), so the absolute path is the fallback."""
    if not TESSERACT:
        return None
    r = subprocess.run([TESSERACT, "--list-langs"], capture_output=True, text=True)
    return [l.strip() for l in r.stdout.splitlines()[1:] if l.strip()]


def preprocess(png, out, blur_pitches=LOWPASS_PITCHES, upscale=UPSCALE):
    """Upscale, low-pass at `blur_pitches` x the pitch, invert (dark text on light),
    threshold at the midpoint — the picture tesseract reads. Returns the path."""
    from PIL import Image, ImageFilter
    im = Image.open(png).convert("L")
    im = im.resize((im.width * upscale, im.height * upscale), Image.BICUBIC)
    im = im.filter(ImageFilter.GaussianBlur(blur_pitches * PITCH_PX * upscale / 4 * 1.0))
    im = Image.eval(im, lambda v: 255 - v)
    lo, hi = im.getextrema()
    im = im.point(lambda v: 255 if v > (lo + hi) / 2 else 0)
    im.save(out)
    return out


def ocr(png, lang):
    r = subprocess.run([TESSERACT, png, "-", "--psm", "7", "-l", lang], capture_output=True, text=True)
    return r.stdout.strip()


def render_case(font, text, rows, offset_rows, out_png, gamma=None, width=420):
    import render_qml as RQ
    import make_notify_marquee as NM
    kw = dict(font=font, text=text, backdrop_rows=rows, offset_rows=offset_rows)
    if gamma is not None:
        kw["gamma"] = gamma
    qml = NM.aperture_text_probe_qml("file:" + os.path.join(ROOT, "templates"), **kw)
    # the software scene graph, like check_aperture: the field is arithmetic and
    # draws the same pixels on either backend, and the gate's environment has no
    # GL context (measured s131: four "Failed to create QRhi" withholds under paperkit)
    return RQ.render_document(qml, "EL-Openglo", width, 40, out_png, software=True)


def measure(cases=CASES, blur=LOWPASS_PITCHES, gamma=None):
    import render_qml as RQ
    langs = languages()
    rows = []
    for label, font, text, lang, nrows, off in cases:
        row = {"label": label, "font": font, "text": text, "lang": lang, "rows": nrows}
        if langs is None:
            row["withheld"] = "tesseract is not on this host"
        elif lang not in langs:
            row["withheld"] = f"tessdata for {lang} is not installed (have {', '.join(langs)})"
        elif not os.path.exists(RQ.QML):
            row["withheld"] = f"{RQ.QML} is not installed"
        else:
            with tempfile.TemporaryDirectory() as td:
                png = os.path.join(td, "board.png")
                rc, err = render_case(font, text, nrows, off, png, gamma=gamma)
                if rc != 0 or not os.path.isfile(png):
                    row["withheld"] = f"render failed: {err[-200:]}"
                else:
                    read = ocr(preprocess(png, os.path.join(td, "ocr.png"), blur), lang)
                    row.update(read=read, score=round(similarity(text, read), 3))
        rows.append(row)
    return {"cases": rows, "blur_pitches": blur, "gamma": gamma}


def sweep():
    """γ x blur over the 1:1 AND the 2:1 Latin cases: the score per point, the best
    named per case. ⚑ γ IS THE IDENTITY AT 1:1 (measured s131: sixteen points, four
    γ values, identical reads) — every pip is exactly 0 or 1 coverage there, and
    coverage^γ moves nothing on {0, 1}; only the 2:1 case, where a stroke half-fills
    an aperture, can be moved by it."""
    grid = []
    for case in [c for c in CASES if c[0] in ("latin-unifont-1to1", "latin-unifont-2to1")]:
        for gamma in (1.0, 0.7, 0.5, 0.35):
            for blur in (1.0, 1.5, 2.0):
                m = measure([case], blur=blur, gamma=gamma)["cases"][0]
                grid.append({"case": case[0], "gamma": gamma, "blur": blur, "score": m.get("score"),
                             "read": m.get("read"), "withheld": m.get("withheld")})
    return grid


def main(argv):
    known = {"--json", "--sweep", "--selftest"}
    for a in argv[1:]:
        if a not in known:
            print(f"check_legibility: unknown flag {a!r}", file=sys.stderr)
            return 2
    if "--sweep" in argv:
        grid = sweep()
        for g in grid:
            print(f"  {g['case']:20s} gamma {g['gamma']:.2f} blur {g['blur']:.1f}  score {g['score']}  read {g['read']!r}" if g["score"] is not None
                  else f"  {g['case']:20s} gamma {g['gamma']:.2f} blur {g['blur']:.1f}  WITHHELD {g['withheld']}")
        for case in sorted({g["case"] for g in grid}):
            scored = [g for g in grid if g["case"] == case and g["score"] is not None]
            if scored:
                b = max(scored, key=lambda g: g["score"])
                spread = max(g["score"] for g in scored) - min(g["score"] for g in scored)
                print(f"check_legibility --sweep {case}: best gamma {b['gamma']} blur {b['blur']} score {b['score']} "
                      f"(spread {spread:.3f}) over {len(scored)} of {len([g for g in grid if g['case'] == case])} points")
        return 0
    m = measure()
    if "--json" in argv:
        print(json.dumps(m, indent=1))
        return 0
    for r in m["cases"]:
        if "withheld" in r:
            print(f"  {r['label']:22s} WITHHELD {r['withheld']}")
        else:
            print(f"  {r['label']:22s} score {r['score']:.3f}  read {r['read']!r}  for {r['text']!r}")
    print(f"check_legibility: {sum(1 for r in m['cases'] if 'score' in r)} of {len(m['cases'])} cases scored; the verdict is `opa_gate.py legibility`")
    return 0


def _selftest():
    ok = True

    def chk(label, got, want):
        nonlocal ok
        print(f"  {'ok  ' if got == want else 'FAIL'} {label}" + ("" if got == want else f": got {got!r} want {want!r}"))
        ok = ok and got == want

    chk("an exact read scores 1", similarity("Hello world", "Hello world"), 1.0)
    chk("an empty read scores 0", similarity("Hello", ""), 0.0)
    chk("one wrong letter of five costs a fifth", similarity("Hello", "Mello"), 0.8)
    chk("whitespace is collapsed before scoring", similarity("a  b", "a b"), 1.0)
    # the pre-processing can SEE: a field of separate dots becomes connected strokes
    # after the low-pass — a 3-px dot row at 4-px pitch reads as one bar
    from PIL import Image
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        im = Image.new("L", (80, 20), 20)
        for c in range(5, 15):
            for dx in range(3):
                for dy in range(3):
                    im.putpixel((c * 4 + dx, 8 + dy), 255)
        p = os.path.join(td, "dots.png")
        im.save(p)
        out = Image.open(preprocess(p, os.path.join(td, "out.png"))).convert("L")
        # along the bar's row (upscaled), the dark run is continuous: no light gap between dots
        y = 9 * UPSCALE
        row = [out.getpixel((x, y)) for x in range(5 * 4 * UPSCALE, 15 * 4 * UPSCALE)]
        chk("the low-pass connects the dots into one stroke", all(v == 0 for v in row[UPSCALE * 2:-UPSCALE * 2]), True)
    chk("a missing tessdata is withheld, not scored",
        "withheld" in measure((("x", "Unifont", "a", "xx_nolang", 8, 0),))["cases"][0], True)
    print("check_legibility selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    os.chdir(ROOT)
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
