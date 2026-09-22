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

# ⚑ THE SWITCHER'S RUNTIME IS KWIN'S, NOT PLASMA'S (W52): KWin.TabBoxSwitcher
# supplies model / currentIndex / visible / screenGeometry, PlasmaCore.Dialog is
# a window, PlasmaComponents3.Label is a Text, and i18ndc is KDE's. Each becomes
# the plain-QML thing it is, and the model becomes a stub of three captions with
# the middle one current — the smallest task list that shows lit, ghost and the
# minimized weight at once. Listed here so the whole gap between harness and
# KWin is legible; nothing else in the emitted document is touched.
SWITCHER_SUBSTITUTIONS = (
    (r"^import org\.kde\.kwin as KWin\n", ""),
    (r"^KWin\.TabBoxSwitcher \{",
     "Item {\n"
     "    property var model: stubModel\n"
     "    property int currentIndex\n"
     "    property rect screenGeometry: Qt.rect(0, 0, width, height)\n"
     "    function i18ndc(d, c, s) { return s }\n"
     "    ListModel {\n"
     "        id: stubModel\n"
     "        ListElement { caption: \"Konsole\"; icon: \"utilities-terminal\"; minimized: false }\n"
     "        ListElement { caption: \"Dolphin — Home\"; icon: \"system-file-manager\"; minimized: false }\n"
     "        ListElement { caption: \"Firefox\"; icon: \"firefox\"; minimized: true }\n"
     "        function longestCaption() { return \"Dolphin — Home\" }\n"
     "        function activate(i) {}\n"
     "    }\n"
     "    Component.onCompleted: list.currentIndex = 1"),
    (r"^    PlasmaCore\.Dialog \{\n        id: dialog\n        location:[^\n]*\n        visible:[^\n]*\n        flags:[^\n]*\n        x:[^\n]*\n        y:[^\n]*\n",
     "    Item {\n        id: dialog\n        anchors.fill: parent\n"),
    (r"mainItem: Item \{", "Item {\n            anchors.centerIn: parent"),
    (r"PlasmaComponents3\.Label", "Text"),
    (r"\n        onSceneGraphError: \(\) => \{\n[^\n]*\n        \}\n", "\n"),
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
        # ONE package since W35: the emission has no variant; the variant is the
        # scheme it is rendered under (theme_probe.env_for, in render())
        qml, kcfg = make_clock.main_qml(), make_clock.CONFIG_XML
    elif surface == "live-wallpaper":
        import make_wallpaper_live
        qml = make_wallpaper_live.main_qml()      # one package since W35
        kcfg = make_wallpaper_live.config_main_xml()
    elif surface == "switcher":
        import make_taskswitch
        qml, kcfg = make_taskswitch.main_qml(), ""
        for pat, rep in SWITCHER_SUBSTITUTIONS:
            qml, n = re.subn(pat, rep, qml, flags=re.M)
            if n == 0:
                raise ValueError(f"switcher rewrite: {pat[:40]!r} matched nothing — the template moved under the harness")
    elif surface == "aperture":
        # W54's probe: the aperture field over a synthetic edge block, bound to the
        # theme like a shipped surface; ApertureField.qml is imported from templates/
        import make_notify_marquee
        qml = make_notify_marquee.aperture_probe_qml("file:" + os.path.join(ROOT, "templates"))
        kcfg = ""
    elif surface == "aperture-text":
        import make_notify_marquee
        qml = make_notify_marquee.aperture_text_probe_qml("file:" + os.path.join(ROOT, "templates"))
        kcfg = ""
    else:
        raise ValueError(f"unknown surface {surface!r}; clock, live-wallpaper, switcher, aperture or aperture-text")
    for pat, rep in SUBSTITUTIONS:
        qml = re.sub(pat, rep, qml, flags=re.M)
    return qml, _kcfg_defaults(kcfg), cols["ground"]


def render(surface, variant, w, h, out_png, config_override=None, software=False):
    """Render to out_png; returns (rc, stderr). `software` asks for the software
    scene graph explicitly (what the ebuild sandbox gets anyway) — an argument, not
    an environment mutation: render_screens once set EL_RENDER_SOFTWARE in its own
    process for one animation and every later still rendered under it (s125)."""
    qml, config, ground = subject(surface, variant)
    if config_override:
        config.update(config_override)
    return render_document(qml, variant, w, h, out_png, config, ground, software)


def render_document(qml, variant, w, h, out_png, config=None, ground=None, software=False):
    """Render an already-rewritten QML document under `variant`'s scheme (the probe
    with its own holes — check_legibility renders the text probe per case). The
    harness, environment and backend rules are render()'s."""
    if config is None:
        config = {}
    if ground is None:
        import make_preview
        ground = make_preview.parse_scheme(variant)["ground"]
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
        # ⚑ AND UNDER THE REAL THEME (W35): a bound surface reads Kirigami.Theme,
        # so the run happens in theme_probe.env_for(variant) — the KDE platform
        # theme on a private kdeglobals that IS the variant's .colors — as a
        # widgets app. An unbound surface is unaffected by it.
        import theme_probe as TP
        xdg = os.path.join(td, "xdg")
        os.makedirs(xdg)
        env = TP.env_for(variant, xdg)
        env.update(QT_LOGGING_RULES="*.debug=false;kf.kirigami.platform=false",
                   QT_QUICK_BACKEND="rhi", QSG_RHI_BACKEND="opengl", QSG_INFO="1")
        # ⚑ UNDER A BUILD SANDBOX THE GPU IS A VIOLATION, NOT A RESOURCE.  Opening
        # /dev/nvidiactl under sys-apps/sandbox failed the whole staging (measured
        # 2026-09-21, check_ebuild). Portage's sandbox sets SANDBOX_ON; there the
        # software scene graph draws the lit pixels the render gate asks for, and
        # the halo (MultiEffect) is simply absent — reported as backend=software.
        if software or os.environ.get("SANDBOX_ON") == "1" or os.environ.get("EL_RENDER_SOFTWARE") == "1":
            env["QT_QUICK_BACKEND"] = "software"
            env.pop("QSG_RHI_BACKEND", None)
        r = subprocess.run([QML, "--apptype", "widget", os.path.join(td, "harness.qml")], env=env,
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


def edges(png, variant):
    """How SOFT are this surface's stroke edges? (W33; the operator: the live
    wallpaper looks 'like Minecraft sans RTX' beside the clock.) Project every
    pixel onto the ground→lit axis and count the TRANSITION pixels — litness
    strictly between 0.15 and 0.85, i.e. neither on nor off. An antialiased,
    round-capped stroke carries a rim of them; a hard polygon edge carries almost
    none. Reported as a fraction of the pixels that are lit at all, so it does not
    depend on how much of the surface is text. The ground is read from the picture
    (its modal colour), not assumed: a surface may draw its own void."""
    from PIL import Image
    import make_preview
    lit = tuple(int(make_preview.parse_scheme(variant)["phosphor"][i:i + 2], 16) for i in (1, 3, 5))
    im = Image.open(png).convert("RGB")
    colours = im.getcolors(im.width * im.height) or []
    ground = max(colours)[1] if colours else (0, 0, 0)
    lg = [l - g for l, g in zip(lit, ground)]
    norm = sum(v * v for v in lg) or 1
    px = im.load()
    L = [[sum((px[x, y][i] - ground[i]) * lg[i] for i in range(3)) / norm
          for x in range(im.width)] for y in range(im.height)]
    # ⚑ ONLY A PIXEL TOUCHING A LIT ONE IS AN EDGE (measured s132: counting every
    # intermediate pixel made the wallpaper read 0.829 "softer" than the clock's
    # 0.143 — it was counting the GHOST segments, a flat band at the ghost alpha,
    # as edge. A ghost's own interior touches no lit pixel; its rim does, and that
    # rim IS an edge.)
    on = trans = 0
    for y in range(im.height):
        for x in range(im.width):
            v = L[y][x]
            if v >= 0.85:
                on += 1
            elif v > 0.15 and any(L[y + dy][x + dx] >= 0.85
                                  for dy in (-1, 0, 1) for dx in (-1, 0, 1)
                                  if 0 <= y + dy < im.height and 0 <= x + dx < im.width):
                trans += 1
    return {"png": os.path.basename(png), "variant": variant, "ground": "#%02x%02x%02x" % ground,
            "lit_px": on, "edge_px": trans,
            "softness": round(trans / on, 3) if on else None}


def main(argv):
    known = {"--variant", "--width", "--height", "--png", "--pixels", "--edges", "--set"}
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
    surface = next((a for a in args if not a.startswith("--") and a in ("clock", "live-wallpaper", "switcher", "aperture", "aperture-text")), None)
    if surface is None:
        print("render_qml: name a surface: clock | live-wallpaper | switcher | aperture | aperture-text", file=sys.stderr)
        return 2
    variant = opt("--variant", "EL-Openglo")
    default_h = {"clock": 48, "switcher": 200, "aperture": 40, "aperture-text": 40}.get(surface, 400)
    w, h = int(opt("--width", 400)), int(opt("--height", default_h))
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
    if "--edges" in args:
        e = edges(out, variant)
        print(f"  ground    {e['ground']} (the picture's own modal colour)")
        print(f"  lit       {e['lit_px']} px")
        print(f"  edge      {e['edge_px']} px (intermediate AND touching a lit pixel)")
        print(f"  softness  {e['softness']} (edge per lit pixel; a hard polygon edge is near 0)")
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
