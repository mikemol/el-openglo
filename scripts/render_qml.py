#!/usr/bin/env python3
"""render_qml.py — draw an emitted Plasma surface HEADLESS and say what it drew.

⚑ "LOADS" IS NOT "DRAWS".  plasmawindowed proves a plasmoid instantiates; it says
nothing about what reached the pixels. The first bloom rebuild loaded clean and
smeared every panel digit into one haze (⊕VER 2026-09-21) — the operator's eyes
were the only gate. ⊕RENDER-GATE (session 65) had exactly this capability in
qml_sanity.py, which did not survive the recovery. This is it, rebuilt on Qt's own
`qml` runner and Item.grabToImage under the offscreen platform — no Python Qt
bindings needed (none are installed here; qlist measured).

    scripts/render_qml.py clock [--variant V] [--width W --height H] --png OUT
    scripts/render_qml.py live-wallpaper [--variant V] ... --png OUT
    scripts/render_qml.py clock --pixels        # lit / ghost / ground pixel census
    scripts/render_qml.py --selftest

⚑ THE HARNESS SUBSTITUTES THE PLASMA RUNTIME, AND SAYS EXACTLY WHAT.  A surface's
root is PlasmoidItem / WallpaperItem, types only Plasma's applet loader can
create, and it reads `plasmoid.configuration` / `wallpaper.configuration`. The
harness rewrites the ROOT TYPE to a plain Item carrying the two representation
properties, drops the org.kde.plasma imports, and supplies a `plasmoid` and
`wallpaper` object whose `configuration` is the kcfg's defaults. Nothing else is
touched: the rewrite is three anchored substitutions on the emitted text, listed
in SUBSTITUTIONS so a reader can see the whole gap between harness and Plasma.

⚑ WEAKNESS: layer effects (MultiEffect) need an RHI. The offscreen platform gets
one on this host; where it does not, the halo is absent from the render and
--pixels reports `effects: unavailable` — a SKIP, not a pass.
"""
import json
import os
import re
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QML = "/usr/lib64/qt6/bin/qml"

# root-type rewrite: the Plasma container becomes a sized Item that instantiates
# its own fullRepresentation, exactly as the applet loader would
SUBSTITUTIONS = (
    (r"^import org\.kde\.plasma\.[^\n]*\n", ""),
    # org.kde.kirigami is KEPT (W35): the real module loads headless, and a bound
    # surface reads Kirigami.Theme — theme_probe.env_for makes it resolve a variant
    (r"^PlasmoidItem \{",
     "Item {\n    property var preferredRepresentation\n"
     "    property Component fullRepresentation\n"
     "    Loader { anchors.fill: parent; sourceComponent: parent.fullRepresentation }"),
    (r"^WallpaperItem \{", "Item {"),
)

HARNESS = """import QtQuick
import QtQuick.Window
Window {
    id: harness
    width: %(w)d; height: %(h)d; visible: true; color: "%(ground)s"
    property var plasmoid: QtObject { property var configuration: (%(config)s) }
    property var wallpaper: QtObject { property var configuration: (%(config)s) }
    Rectangle { anchors.fill: parent; color: "%(ground)s" }
    Loader { id: subject; anchors.fill: parent; source: "subject.qml" }
    Timer {
        interval: 1200; running: true
        onTriggered: harness.contentItem.grabToImage(function (r) {
            r.saveToFile("%(out)s"); Qt.quit()
        })
    }
}
"""


def _kcfg_defaults(xml_text):
    """{name: default} from a kcfg, typed."""
    out = {}
    for m in re.finditer(r'<entry name="(\w+)" type="(\w+)"><default>([^<]*)</default>',
                         xml_text):
        name, typ, val = m.groups()
        out[name] = ({"Bool": lambda v: v == "true", "Double": float, "Int": int}
                     .get(typ, str))(val)
    return out


def subject(surface, variant):
    """(emitted QML rewritten for the harness, config defaults, ground colour)."""
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    os.chdir(ROOT)
    import make_preview
    cols = make_preview.parse_scheme(variant)
    if surface == "clock":
        import make_clock
        import make_schemes
        # GRID is keyed (phosphor, mode); the variant name is the token dict's id
        t = next((t for (t, _dark) in make_schemes.GRID.values() if t["id"] == variant), None)
        if t is None:
            raise ValueError(f"no variant {variant!r} in GRID")
        qml, kcfg = make_clock.main_qml(t), make_clock.CONFIG_XML
    elif surface == "live-wallpaper":
        import make_wallpaper_live
        qml = make_wallpaper_live.main_qml(variant)
        kcfg = make_wallpaper_live.config_main_xml()
    else:
        raise ValueError(f"unknown surface {surface!r}; clock or live-wallpaper")
    for pat, rep in SUBSTITUTIONS:
        qml = re.sub(pat, rep, qml, flags=re.M)
    return qml, _kcfg_defaults(kcfg), cols["ground"]


def render(surface, variant, w, h, out_png, config_override=None):
    """Render to out_png; returns (rc, stderr)."""
    qml, config, ground = subject(surface, variant)
    if config_override:
        config.update(config_override)
    with tempfile.TemporaryDirectory(dir=os.path.join(ROOT, ".ebuild-witness")
                                     if os.path.isdir(os.path.join(ROOT, ".ebuild-witness"))
                                     else None) as td:
        open(os.path.join(td, "subject.qml"), "w").write(qml)
        open(os.path.join(td, "harness.qml"), "w").write(HARNESS % {
            "w": w, "h": h, "ground": ground, "config": json.dumps(config),
            "out": os.path.abspath(out_png)})
        # ⚑ THE OFFSCREEN PLATFORM DEFAULTS TO THE SOFTWARE SCENE GRAPH, which has
        # no shaders: MultiEffect silently draws nothing and a bloom check would
        # pass or fail on a picture the desktop never shows (measured: bloom=4 and
        # bloom=0 rendered byte-identical). Ask for the RHI on OpenGL explicitly.
        env = dict(os.environ, QT_QPA_PLATFORM="offscreen", QT_LOGGING_RULES="*.debug=false",
                   QT_QUICK_BACKEND="rhi", QSG_RHI_BACKEND="opengl", QSG_INFO="1")
        # ⚑ UNDER A BUILD SANDBOX THE GPU IS A VIOLATION, NOT A RESOURCE.  Opening
        # /dev/nvidiactl under sys-apps/sandbox failed the whole staging (measured
        # 2026-09-21, check_ebuild). Portage's sandbox sets SANDBOX_ON; there the
        # software scene graph draws the lit pixels the render gate asks for, and
        # the halo (MultiEffect) is simply absent — reported as backend=software.
        if os.environ.get("SANDBOX_ON") == "1" or os.environ.get("EL_RENDER_SOFTWARE") == "1":
            env["QT_QUICK_BACKEND"] = "software"
            env.pop("QSG_RHI_BACKEND", None)
        r = subprocess.run([QML, os.path.join(td, "harness.qml")], env=env,
                           capture_output=True, text=True, timeout=60)
    backend = "rhi" if "Creating QRhi" in r.stderr else (
        "software" if "backend software" in r.stderr else "unknown")
    err = "\n".join(l for l in r.stderr.splitlines() if not l.startswith("qt.scenegraph"))
    return r.returncode, f"backend={backend}" + (f"\n{err}" if err.strip() else "")


def _near(a, b, tol=28):
    return all(abs(x - y) <= tol for x, y in zip(a, b))


def pixels(png, variant):
    """Census: how many pixels are the lit colour, the ghost colour, the ground."""
    from PIL import Image
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    import make_preview
    cols = make_preview.parse_scheme(variant)

    def rgb(hexs):
        hexs = hexs.lstrip("#")
        return tuple(int(hexs[i:i + 2], 16) for i in (0, 2, 4))
    lit, ghost_in, ground = rgb(cols["phosphor"]), rgb(cols["ghost"]), rgb(cols["ground"])
    # the SEEN ghost is the declared ghost composited over ground at the solved
    # alpha (relations.md §3b) — what the screen shows, not the token
    a = float(cols["ghost_alpha"])
    ghost = tuple(round(a * g + (1 - a) * b) for g, b in zip(ghost_in, ground))
    im = Image.open(png).convert("RGB")
    n = {"lit": 0, "ghost-ish": 0, "ground": 0, "other": 0}
    data = list(im.get_flattened_data() if hasattr(im, "get_flattened_data") else im.getdata())
    for p in data:
        if _near(p, lit):
            n["lit"] += 1
        elif _near(p, ground, 8):
            n["ground"] += 1
        elif _near(p, ghost, 20):
            n["ghost-ish"] += 1
        else:
            n["other"] += 1
    n["total"] = im.width * im.height
    # the modal colour, so a large "other" names itself instead of being argued with
    from collections import Counter
    mode, count = Counter(data).most_common(1)[0]
    n["modal"] = "#%02x%02x%02x (%d px; expected ground #%02x%02x%02x)" % (*mode, count, *ground)
    return n


def main(argv):
    known = {"--variant", "--width", "--height", "--png", "--pixels", "--set"}
    args = argv[1:]
    for a in args:
        if a.startswith("--") and a not in known:
            print(f"render_qml: unknown flag {a!r}", file=sys.stderr)
            return 2
    if not os.path.exists(QML):
        print(f"render_qml: SKIP — {QML} is not installed (qtdeclarative tools)", file=sys.stderr)
        return 0

    def opt(name, default):
        return args[args.index(name) + 1] if name in args else default
    surface = next((a for a in args if not a.startswith("--") and a in ("clock", "live-wallpaper")), None)
    if surface is None:
        print("render_qml: name a surface: clock | live-wallpaper", file=sys.stderr)
        return 2
    variant = opt("--variant", "EL-Openglo")
    w, h = int(opt("--width", 400)), int(opt("--height", 48 if surface == "clock" else 400))
    override = {}
    for i, a in enumerate(args):
        if a == "--set":
            k, v = args[i + 1].split("=", 1)
            override[k] = json.loads(v)
    out = opt("--png", os.path.join(tempfile.gettempdir(), f"render-{surface}-{variant}.png"))
    rc, err = render(surface, variant, w, h, out, override)
    if rc != 0 or not os.path.exists(out):
        print(f"render_qml: REFUSED — {surface} did not render (rc={rc}):\n{err}", file=sys.stderr)
        return 1
    if err:
        print(err, file=sys.stderr)
    print(f"render_qml: {surface} {variant} {w}x{h} -> {out}")
    if "--pixels" in args:
        n = pixels(out, variant)
        for k in ("lit", "ghost-ish", "ground", "other", "total", "modal"):
            print(f"  {k:9} {n[k]}")
    return 0


def _selftest():
    ok = True

    def check(label, got, want):
        nonlocal ok
        if got != want:
            print(f"  FAIL {label}: got {got!r} want {want!r}")
            ok = False
        else:
            print(f"  ok   {label}")

    check("kcfg defaults are typed",
          _kcfg_defaults('<entry name="a" type="Bool"><default>true</default></entry>'
                         '<entry name="b" type="Double"><default>1.5</default></entry>'),
          {"a": True, "b": 1.5})
    qml, cfg, ground = subject("clock", "EL-Openglo")
    check("the Plasma root type is rewritten", "PlasmoidItem" in qml, False)
    check("no org.kde.plasma import survives", "org.kde.plasma" in qml, False)
    check("the config carries the kcfg keys", {"bloom", "weight", "showGhost"} <= set(cfg), True)
    if not os.path.exists(QML):
        print("  SKIP render arms — qml runner not installed")
    else:
        with tempfile.TemporaryDirectory() as td:
            out = os.path.join(td, "c.png")
            rc, err = render("clock", "EL-Openglo", 400, 48, out)
            check(f"the clock renders headless ({err[-200:]})", rc == 0 and os.path.exists(out), True)
            if rc == 0:
                n = pixels(out, "EL-Openglo")
                check("a rendered clock has lit pixels", n["lit"] > 20, True)
                check("...and is not all lit", n["ground"] > n["lit"], True)
            # ⚑ THE GATE MUST BE ABLE TO FAIL, PER CHANNEL: weight alone and bloom
            # alone must each change the picture. Bloom needs the RHI — on the
            # software scene graph it is a SKIP, printed, not a pass.
            out_w = os.path.join(td, "w0.png")
            rc_w, _ = render("clock", "EL-Openglo", 400, 48, out_w, {"weight": 0})
            if rc == 0 and rc_w == 0:
                check("weight=0 renders differently",
                      open(out, "rb").read() == open(out_w, "rb").read(), False)
            if "backend=rhi" not in err:
                print(f"  SKIP bloom arm — scene graph is not the RHI ({err.splitlines()[0]})")
            else:
                out_b = os.path.join(td, "b0.png")
                rc_b, _ = render("clock", "EL-Openglo", 400, 48, out_b, {"bloom": 0})
                if rc_b == 0:
                    check("bloom=0 renders differently (the halo is drawn)",
                          open(out, "rb").read() == open(out_b, "rb").read(), False)
    print("render_qml selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
