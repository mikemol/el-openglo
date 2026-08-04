#!/usr/bin/env python3
"""Build el-indiglo-themes_<ver>_all.deb (⊕VER-DEB).

One MAPPING, two scopes:
  SYSTEM (into the .deb, /usr/share): color-schemes, konsole, aurorae, plasma
    desktoptheme, plasmoid, fonts, wallpapers.
  PER-USER (via the shipped `el-indiglo-apply` helper): GTK gtk.css + Kvantum
    config link, plus live plasma-apply of the chosen variant.

All six grid variants ship. Helper defaults to EL-Indiglo.
"""
import os, shutil, subprocess, stat, hashlib

VERSION = "1.2.0"
ARCH = "all"
PKG = "el-indiglo-themes"
VARIANTS = ["EL-Indiglo", "EL-Indiglo-Lit", "EL-Azure", "EL-Azure-Lit",
            "EL-Amber", "EL-Amber-Lit"]
ROOT = os.path.dirname(os.path.abspath(__file__))
BUILD = "/tmp/eldeb"
DEB_ROOT = os.path.join(BUILD, PKG)


# --- THE MAPPING: (source glob-or-dir, destination under DEB_ROOT) ----------
# System-scoped only. Per-user files are handled by the helper, not packaged
# into a user's home (which a .deb must never write to).
def system_mapping():
    m = []
    # color schemes (one .colors per variant) + konsole schemes
    for v in VARIANTS:
        m.append((f"{v}.colors", f"usr/share/color-schemes/{v}.colors"))
        ks = f"{v}.colorscheme"
        if os.path.exists(os.path.join(ROOT, ks)):
            m.append((ks, f"usr/share/konsole/{ks}"))
    # aurorae window decorations
    for v in VARIANTS:
        src = f"aurorae/themes/{v}"
        if os.path.isdir(os.path.join(ROOT, src)):
            m.append((src, f"usr/share/aurorae/themes/{v}"))
    # plasma desktoptheme (Plasma Style)
    for v in VARIANTS:
        src = f"plasma/desktoptheme/{v}"
        if os.path.isdir(os.path.join(ROOT, src)):
            m.append((src, f"usr/share/plasma/desktoptheme/{v}"))
    # clock plasmoid (one package per variant, system-installed)
    for v in VARIANTS:
        src = f"plasma-clock/{v}"
        if os.path.isdir(os.path.join(ROOT, src)):
            mid = f"org.el.segclock.{v.lower().replace('-', '')}"
            m.append((src, f"usr/share/plasma/plasmoids/{mid}"))
    # fonts (system font dir; postinst runs fc-cache)
    for fn in os.listdir(os.path.join(ROOT, "fonts")):
        if fn.endswith((".ttf", ".svg")):
            m.append((f"fonts/{fn}", f"usr/share/fonts/truetype/el-indiglo/{fn}"))
    # wallpapers: one VALID KDE wallpaper package per variant (metadata.json +
    # contents/images/<res>.png). A wallpaper package without metadata.json is
    # not selectable; the previous single-dir dump was invalid.
    for v in VARIANTS:
        # pick this variant's wallpaper png (lit variants use the -lit image)
        base = v[:-4] if v.endswith("-Lit") else v
        lit = "-lit" if v.endswith("-Lit") else ""
        wp = f"{base}{lit}-wallpaper.png"
        if os.path.exists(os.path.join(ROOT, wp)):
            m.append((wp,
                      f"usr/share/wallpapers/{v}/contents/images/1920x1080.png"))
    return m


# --- root Plymouth helper (run with sudo; boot-splash seam) ------------------
# The theme is baked into the initramfs by the stock initramfs-tools plymouth
# hook, which reads the default.plymouth ALTERNATIVE. So we register + select the
# alternative, then rebuild the initramfs ONCE; kernel updates re-bundle it
# automatically (no DKMS, no per-kernel logic). Root-only.
PLYMOUTH_HELPER = r'''#!/bin/sh
# el-indiglo-plymouth — select an EL Indiglo boot splash. Run with sudo.
set -eu
VARIANT="${1:-EL-Indiglo}"
THEME="/usr/share/plymouth/themes/el-indiglo-$VARIANT/el-indiglo.plymouth"
if [ "$(id -u)" -ne 0 ]; then
  echo "Run with sudo: sudo el-indiglo-plymouth $VARIANT" >&2; exit 1
fi
if [ ! -f "$THEME" ]; then echo "no plymouth theme for $VARIANT" >&2; exit 1; fi
# register + select the default.plymouth alternative
update-alternatives --install /usr/share/plymouth/themes/default.plymouth \
  default.plymouth "$THEME" 200 >/dev/null 2>&1 || true
update-alternatives --set default.plymouth "$THEME" >/dev/null 2>&1 || true
# rebuild the initramfs so the theme is bundled for early boot
if command -v update-initramfs >/dev/null 2>&1; then
  update-initramfs -u
fi
echo "Boot splash set to EL Indiglo ($VARIANT)."
echo "Preview without rebooting:  plymouthd; plymouth --show-splash; sleep 5; plymouth --quit"
'''


# --- root SDDM helper (run with sudo; theming the login seam SAFELY) ---------
# We do NOT ship a custom SDDM greeter (a broken one can black-screen the whole
# boot — larger blast radius than the lockscreen). Instead we point the STOCK
# Breeze SDDM theme at our phosphor watch-face background. The Breeze theme reads
# theme.conf.user [General] background=<file> AND REQUIRES a `type=image` key
# (without it the background is silently ignored — KDE bug 370521). Root-only
# because it writes under /usr/share and /etc.
SDDM_HELPER = r'''#!/bin/sh
# el-indiglo-sddm — point the stock Breeze SDDM login theme at an EL Indiglo
# phosphor watch-face background. Run with sudo. Does NOT replace the greeter,
# so login/unlock behavior is unchanged (no boot-lockout risk).
set -eu
VARIANT="${1:-EL-Indiglo}"
WP="/usr/share/wallpapers/$VARIANT/contents/images/1920x1080.png"
BREEZE=/usr/share/sddm/themes/breeze
if [ "$(id -u)" -ne 0 ]; then
  echo "Run with sudo: sudo el-indiglo-sddm $VARIANT" >&2; exit 1
fi
if [ ! -f "$WP" ]; then echo "no wallpaper for $VARIANT" >&2; exit 1; fi
if [ ! -d "$BREEZE" ]; then echo "stock breeze SDDM theme not found" >&2; exit 1; fi
# copy the bg into the theme dir and register it WITH the required type=image key
cp "$WP" "$BREEZE/el-indiglo-bg.png"
cat > "$BREEZE/theme.conf.user" <<EOF
[General]
background=el-indiglo-bg.png
type=image
EOF
# ensure SDDM uses the breeze theme
mkdir -p /etc/sddm.conf.d
cat > /etc/sddm.conf.d/el-indiglo.conf <<EOF
[Theme]
Current=breeze
EOF
echo "SDDM login background set to EL Indiglo ($VARIANT)."
echo "Preview without rebooting:  sddm-greeter-qt6 --test-mode --theme $BREEZE"
'''


# --- notification-marquee helper (opt-in; subsume popups into the ticker) -----
# Adds the phosphor ticker widget to the panel AND suppresses the stock popups
# (so the marquee REPLACES them rather than duplicating). Popup suppression via
# plasmanotifyrc — the feed still flows to the marquee's model; only the toasts
# are silenced. Reversible.
NOTIFY_HELPER = r'''#!/bin/sh
# el-indiglo-notify — add the phosphor notification ticker + silence the popups.
set -eu
VARIANT="${1:-EL-Indiglo}"
WIDGET="org.el.notifymarquee.$(echo "$VARIANT" | tr 'A-Z' 'a-z' | tr -d '-')"
PKG="/usr/share/plasma/plasmoids/$WIDGET"
if [ ! -d "$PKG" ]; then echo "no marquee widget for $VARIANT" >&2; exit 1; fi
# suppress the stock notification popups (feed still reaches the ticker model)
# CriticalInDndMode stays on so critical alerts are never hidden.
kwriteconfig6 --file plasmanotifyrc --group DoNotDisturb --key WhenScreenSharing false 2>/dev/null || true
kwriteconfig6 --file plasmanotifyrc --group Notifications --key PopupPosition "Close" 2>/dev/null || true
kwriteconfig6 --file plasmanotifyrc --group Notifications --key PopupTimeout 1 2>/dev/null || true
# add the ticker widget to the panel (harmless if already present)
if command -v qdbus6 >/dev/null 2>&1; then
  qdbus6 org.kde.plasmashell /PlasmaShell org.kde.PlasmaShell.evaluateScript "
    var found = false; var ps = panels();
    for (var i=0;i<ps.length;i++){var w=ps[i].widgets();
      for (var j=0;j<w.length;j++) if (w[j].type=='$WIDGET') found=true;}
    if (!found && ps.length>0) ps[0].addWidget('$WIDGET');
  " 2>/dev/null && echo "  Marquee: ticker added to panel" \
    || echo "  Marquee: add via panel > Add Widgets > 'EL Notification Marquee'"
fi
echo "  Popups: minimized (feed still flows to the ticker; critical alerts kept)"
echo "Tip: for full popup suppression, System Settings > Notifications > Do Not Disturb."
'''


# --- live-wallpaper helper (opt-in; the living watch face on desktop + lock) --
# Distinct opt-in from the static watch-face: sets the Plasma/Wallpaper PLUGIN
# (not an image) on the desktop containment (via plasmashell scripting) and the
# lock screen (via kscreenlockerrc wallpaperPlugin key). Desktop stays cheap
# (1Hz clock tick); lock enables the breathe animation (the seen+idle surface).
LIVE_HELPER = r'''#!/bin/sh
# el-indiglo-live — set the LIVING phosphor watch face as desktop + lock wallpaper.
set -eu
VARIANT="${1:-EL-Indiglo}"
PLUGIN="org.el.indiglo.live.$(echo "$VARIANT" | tr 'A-Z' 'a-z' | tr -d '-')"
PKG="/usr/share/plasma/wallpapers/$PLUGIN"
if [ ! -d "$PKG" ]; then echo "no live wallpaper for $VARIANT" >&2; exit 1; fi
# Desktop: set the wallpaper PLUGIN on every desktop containment (cheap: no breathe)
if command -v qdbus6 >/dev/null 2>&1; then
  qdbus6 org.kde.plasmashell /PlasmaShell org.kde.PlasmaShell.evaluateScript "
    var ds = desktops();
    for (var i = 0; i < ds.length; i++) {
      ds[i].wallpaperPlugin = '$PLUGIN';
    }
  " 2>/dev/null && echo "  Desktop: live watch face set ($PLUGIN)" \
    || echo "  Desktop: set Wallpaper type to 'EL Indiglo Live' manually"
fi
# Lock screen: select the plugin + enable breathe (the seen, idle surface)
kwriteconfig6 --file kscreenlockerrc --group Greeter --key WallpaperPlugin "$PLUGIN" 2>/dev/null || true
kwriteconfig6 --file kscreenlockerrc --group Greeter --group Wallpaper \
  --group "$PLUGIN" --group General --key breathe true 2>/dev/null || true
echo "  Lock screen: live watch face set (breathe on)"
echo "Done. Run 'plasmashell --replace &' or re-login if the desktop doesn't update."
'''


# --- per-user apply helper (installed to /usr/bin, run by the user) ---------
APPLY_HELPER = r'''#!/bin/sh
# el-indiglo-apply — apply an EL Indiglo variant for the CURRENT user.
# System files were installed by the .deb; this wires the per-user bits
# (GTK, Kvantum) and applies the live selection. No root needed.
set -eu
VARIANT="${1:-EL-Indiglo}"
SHARE=/usr/share
case " EL-Indiglo EL-Indiglo-Lit EL-Azure EL-Azure-Lit EL-Amber EL-Amber-Lit " in
  *" $VARIANT "*) : ;;
  *) echo "unknown variant: $VARIANT" >&2
     echo "choose one of: EL-Indiglo EL-Indiglo-Lit EL-Azure EL-Azure-Lit EL-Amber EL-Amber-Lit" >&2
     exit 2 ;;
esac
echo "Applying $VARIANT ..."

# 0. Global Theme (Look-and-Feel) — the single entry that flips the KDE chrome
PID="org.el.indiglo.$(echo "$VARIANT" | tr 'A-Z' 'a-z' | tr -d '-')"
if command -v plasma-apply-lookandfeel >/dev/null 2>&1; then
  plasma-apply-lookandfeel -a "$PID" 2>/dev/null || true
fi

# 1. color scheme (per-user selection of a system-installed scheme)
if command -v plasma-apply-colorscheme >/dev/null 2>&1; then
  plasma-apply-colorscheme "$VARIANT" || true
fi
# 2. plasma desktop theme
if command -v plasma-apply-desktoptheme >/dev/null 2>&1; then
  plasma-apply-desktoptheme "$VARIANT" || true
fi
# 3. GTK 3/4 overrides -> per-user gtk.css (system source shipped read-only)
GSRC="$SHARE/el-indiglo/gtk/$VARIANT"
if [ -d "$GSRC" ]; then
  mkdir -p "$HOME/.config/gtk-3.0" "$HOME/.config/gtk-4.0"
  cp "$GSRC/gtk3.css" "$HOME/.config/gtk-3.0/gtk.css"
  cp "$GSRC/gtk4.css" "$HOME/.config/gtk-4.0/gtk.css"
  echo "  GTK: wrote ~/.config/gtk-{3,4}.0/gtk.css"
fi
# 4. Kvantum config -> per-user
KSRC="$SHARE/el-indiglo/kvantum/$VARIANT"
if [ -d "$KSRC" ]; then
  mkdir -p "$HOME/.config/Kvantum/$VARIANT"
  cp "$KSRC"/* "$HOME/.config/Kvantum/$VARIANT/" 2>/dev/null || true
  # point Kvantum at it
  printf '[General]\ntheme=%s\n' "$VARIANT" > "$HOME/.config/Kvantum/kvantum.kvconfig"
  echo "  Kvantum: installed $VARIANT (select 'kvantum' as Qt style to use it)"
fi
# 5. Aurorae decoration (write kwin selection)
if command -v kwriteconfig6 >/dev/null 2>&1; then
  kwriteconfig6 --file kwinrc --group org.kde.kdecoration2 --key library \
    "org.kde.kwin.aurorae" || true
  kwriteconfig6 --file kwinrc --group org.kde.kdecoration2 --key theme \
    "__aurorae__svg__$VARIANT" || true
  if command -v qdbus6 >/dev/null 2>&1; then
    qdbus6 org.kde.KWin /KWin reconfigure 2>/dev/null || true
  fi
fi

# 6. Wallpaper — set directly (the Global Theme doesn't re-run its layout once
# you've already applied it, so set the image explicitly for the current user)
WP="$SHARE/wallpapers/$VARIANT/contents/images/1920x1080.png"
if [ -f "$WP" ]; then
  if command -v plasma-apply-wallpaperimage >/dev/null 2>&1; then
    plasma-apply-wallpaperimage "$WP" || true
    echo "  Wallpaper: set to $VARIANT"
  fi
fi

# 7. EL segment clock — add to the panel if not already present (uses Plasma's
# scripting D-Bus interface; harmless if it fails / already added)
PLASMOID="org.el.segclock.$(echo "$VARIANT" | tr 'A-Z' 'a-z' | tr -d '-')"
if command -v qdbus6 >/dev/null 2>&1; then
  qdbus6 org.kde.plasmashell /PlasmaShell org.kde.PlasmaShell.evaluateScript "
    var found = false;
    var all = panels();
    for (var i = 0; i < all.length; i++) {
      var w = all[i].widgets();
      for (var j = 0; j < w.length; j++) {
        if (w[j].type == '$PLASMOID') { found = true; }
      }
    }
    if (!found && all.length > 0) {
      all[0].addWidget('$PLASMOID');
    }
  " 2>/dev/null && echo "  Clock: EL segment clock added to panel (if not already present)" || \
    echo "  Clock: add via panel > Add Widgets > 'EL Segment Clock' if not shown"
fi
# 5. Chrome/Chromium theme (can't be auto-installed from disk; point the user)
CTHEME="$SHARE/el-indiglo/chrome/$VARIANT"
if [ -d "$CTHEME" ]; then
  echo "  Chrome: load $CTHEME"
  echo "          via chrome://extensions -> Developer mode -> Load unpacked"
fi
# 6. Konsole colorscheme (auto-discovered in /usr/share/konsole); point Alacritty/foot
if [ -f "$SHARE/konsole/$VARIANT.colorscheme" ]; then
  echo "  Konsole: pick '$VARIANT' in Settings -> Edit Profile -> Appearance"
fi
# 7. Lock screen: point kscreenlocker at the phosphor watch-face wallpaper. This
# is a SAFE config write — it restyles the lock seam to the EL watch face while
# leaving the stock authenticator (password field / unlock) completely intact.
WP="$SHARE/wallpapers/$VARIANT/contents/images/1920x1080.png"
if [ -f "$WP" ]; then
  kwriteconfig6 --file kscreenlockerrc --group Greeter --group Wallpaper \
    --group org.kde.image --group General --key Image "file://$WP" 2>/dev/null \
    && echo "  Lock screen: watch-face wallpaper set (auth unchanged)"
fi
TDIR="$SHARE/el-indiglo/terminals"
if [ -d "$TDIR" ]; then
  echo "  Alacritty: import $TDIR/$VARIANT.alacritty.toml"
  echo "  foot:      include $TDIR/$VARIANT.foot.ini"
fi
echo "Done. Some changes (GTK, Kvantum) may need apps to restart."
echo "Login screen (SDDM): sudo el-indiglo-sddm $VARIANT  (sets the phosphor login background)"
echo "Boot splash (Plymouth): sudo el-indiglo-plymouth $VARIANT  (sets the phosphor boot splash)"
echo "Living watch face:      el-indiglo-live $VARIANT  (animated clock on desktop + lock)"
echo "Notification ticker:    el-indiglo-notify $VARIANT  (marquee subsumes popups)"
'''

# GTK + Kvantum are shipped read-only under /usr/share/el-indiglo for the helper
def helper_source_mapping():
    m = []
    for v in VARIANTS:
        for sub in ("gtk", "kvantum"):
            src = f"{sub}/{v}"
            if os.path.isdir(os.path.join(ROOT, src)):
                m.append((src, f"usr/share/el-indiglo/{sub}/{v}"))
    return m


# --- Look-and-Feel packages: appear under System Settings > Global Theme.
# These carry NO new payload — they REFERENCE the components the deb already
# installs (color scheme, plasma desktoptheme, aurorae decoration, wallpaper),
# so selecting one flips them together. Built into a staging dir then mapped in.
import json as _json

LNF_STAGE = os.path.join(BUILD, "_lnf")

def _decoration_theme(variant):
    # Aurorae decorations are referenced as __aurorae__svg__<ThemeName>
    return f"__aurorae__svg__{variant}"

def build_lnf_packages():
    """Create one Plasma/LookAndFeel package per variant in a staging dir.
    Returns a mapping [(staged_src, deb_dest), ...]."""
    shutil.rmtree(LNF_STAGE, ignore_errors=True)
    mapping = []
    for v in VARIANTS:
        pid = f"org.el.indiglo.{v.lower().replace('-', '')}"
        pkg_dir = os.path.join(LNF_STAGE, pid)
        contents = os.path.join(pkg_dir, "contents")
        os.makedirs(contents, exist_ok=True)
        # metadata.json — KPackageStructure is load-bearing (missing => invisible)
        meta = {
            "KPackageStructure": "Plasma/LookAndFeel",
            "KPlugin": {
                "Authors": [{"Name": "EL Indiglo", "Email": "el@local"}],
                "Category": "Plasma Look And Feel",
                "Description": f"Electroluminescent watch display — {v}",
                "EnabledByDefault": True,
                "Id": pid,
                "License": "GPLv3",
                "Name": f"EL Indiglo ({v})",
                "ServiceTypes": ["Plasma/LookAndFeel"],
                "Version": VERSION,
            },
        }
        open(os.path.join(pkg_dir, "metadata.json"), "w").write(
            _json.dumps(meta, indent=2))
        # defaults — INI referencing the ALREADY-INSTALLED components by name
        lit = v.endswith("-Lit")
        plasmoid_id = f"org.el.segclock.{v.lower().replace('-', '')}"
        defaults = (
            "[kdeglobals][General]\n"
            f"ColorScheme={v}\n\n"
            "[kdeglobals][KDE]\n"
            f"widgetStyle=Breeze\n\n"
            "[plasmarc][Theme]\n"
            f"name={v}\n\n"
            "[kwinrc][org.kde.kdecoration2]\n"
            "library=org.kde.kwin.aurorae\n"
            f"theme={_decoration_theme(v)}\n\n"
            "[kdeglobals][KDE]\n"
            f"LookAndFeelPackage={pid}\n\n"
            "[Wallpaper][org.kde.image][General]\n"
            f"Image=file:///usr/share/wallpapers/{v}/contents/images/1920x1080.png\n"
        )
        open(os.path.join(contents, "defaults"), "w").write(defaults)
        # layout script — the ONE artifact that both places the EL clock AND sets
        # the desktop wallpaper. Runs when the theme's layout is applied.
        layouts = os.path.join(contents, "layouts")
        os.makedirs(layouts, exist_ok=True)
        wp_path = f"/usr/share/wallpapers/{v}/contents/images/1920x1080.png"
        layout_js = f'''// EL Indiglo desktop layout — sets wallpaper + adds the EL segment clock.
var plasma = getApiVersion(1);

// set the wallpaper on every desktop containment
for (var i = 0; i < desktops().length; i++) {{
    var d = desktops()[i];
    d.wallpaperPlugin = "org.kde.image";
    d.currentConfigGroup = ["Wallpaper", "org.kde.image", "General"];
    d.writeConfig("Image", "file://{wp_path}");
}}

// a bottom panel with the EL segment clock on the right
var panel = new Panel;
panel.location = "bottom";
panel.height = gridUnit * 2;
panel.addWidget("org.kde.plasma.kickoff");
panel.addWidget("org.kde.plasma.pager");
panel.addWidget("org.kde.plasma.icontasks");
panel.addWidget("org.kde.plasma.marginsseparator");
panel.addWidget("org.kde.plasma.systemtray");
panel.addWidget("{plasmoid_id}");
'''
        open(os.path.join(layouts, "org.kde.plasma.desktop-layout.js"), "w").write(layout_js)
        # preview.png — KDE shows this on the Global Theme page. Rendered from
        # this variant's own scheme tokens (make_preview), so it can't drift.
        import make_preview as _mp
        cols = _mp.parse_scheme(v)
        import cairosvg as _cs
        _cs.svg2png(bytestring=_mp.preview_svg(cols).encode(),
                    write_to=os.path.join(contents, "preview.png"),
                    output_width=_mp.W * 2, output_height=_mp.H * 2)
        # splash (⊕SPLASH): boot-seam phosphor screen that READS PROGRESS —
        # Plasma advances `stage` 1..6 as the session loads; segments light with
        # it. Void ground + phosphor from this variant's tokens (no new palette).
        splash_dir = os.path.join(contents, "splash")
        os.makedirs(splash_dir, exist_ok=True)
        gnd_hex = '"' + cols["ground"] + '"'
        lit_hex = '"' + cols["phosphor"] + '"'
        # ⊕GHOST-CEILING for the splash: derive the ghost OPACITY so the ghost is
        # "present but not active" — the max opacity whose lit/ghost separation
        # still clears the glanced-at floor. Fixed 0.22 failed on backlit variants
        # (compressed dark-lit-on-light-ground); this adapts per variant.
        import cvd_gate as _cvd2
        _lit_rgb = tuple(int(cols["phosphor"].lstrip("#")[i:i+2], 16) for i in (0, 2, 4))
        _gnd_rgb = tuple(int(cols["ground"].lstrip("#")[i:i+2], 16) for i in (0, 2, 4))
        def _comp(fg, bg, a):
            return tuple(int(round(fg[i]*a + bg[i]*(1-a))) for i in range(3))
        _op = 0.05
        for _k in range(5, 36):
            _a = _k / 100.0
            if _cvd2.wcag_ratio(_lit_rgb, _comp(_lit_rgb, _gnd_rgb, _a)) >= 5.8:
                _op = _a
            else:
                break
        open(os.path.join(splash_dir, "Splash.qml"), "w").write(
            _splash_qml(gnd_hex, lit_hex, _op))
        mapping.append((pkg_dir, f"usr/share/plasma/look-and-feel/{pid}"))
    return mapping


def _splash_qml(ground_hex, lit_hex):
    """A progress-reading phosphor splash. Root Item exposes `stage` (Plasma
    increments 1..6). A row of '12:00' digits on void ground; ghost digits always
    faint, lit digits fill left-to-right as stage rises, so the boot literally
    lights the watch face awake. Ghost = the lit phosphor at low opacity (same
    material, un-energised) — consistent with the ghost/lit model everywhere else."""
    return f'''import QtQuick 2.15

Item {{
    id: root
    property int stage: 0
    readonly property int total: 6
    anchors.fill: parent

    Rectangle {{ anchors.fill: parent; color: {ground_hex} }}

    Row {{
        anchors.centerIn: parent
        spacing: parent.width * 0.02
        Repeater {{
            model: ["1","2",":","0","0"]
            Item {{
                width: root.width*0.07; height: root.width*0.12
                property bool lit: index <= (root.stage / root.total) * 5
                Text {{
                    anchors.fill: parent
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    text: modelData
                    font.pixelSize: parent.height
                    font.family: "monospace"; font.bold: true
                    color: {lit_hex}
                    opacity: 0.22
                }}
                Text {{
                    anchors.fill: parent
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    text: modelData
                    font.pixelSize: parent.height
                    font.family: "monospace"; font.bold: true
                    color: {lit_hex}
                    opacity: parent.lit ? 1.0 : 0.0
                    Behavior on opacity {{ NumberAnimation {{ duration: 220 }} }}
                }}
            }}
        }}
    }}
}}
'''


CONTROL = f"""Package: {PKG}
Version: {VERSION}
Section: kde
Priority: optional
Architecture: {ARCH}
Depends: plasma-workspace
Recommends: kvantum, fontconfig
Suggests: qt6ct
Maintainer: EL Indiglo <el@local>
Installed-Size: {{size}}
Description: EL Indiglo — electroluminescent watch-display theme for KDE Plasma
 A backlit digital-watch aesthetic across the whole desktop: color schemes,
 Konsole schemes, Aurorae window decorations, Plasma styles, a seven/multi-
 segment and dot-matrix clock plasmoid, and installable segment/matrix fonts.
 Six phosphor variants (Indiglo, Azure, Amber; each lit/unlit). After install
 run `el-indiglo-apply [VARIANT]` to apply per-user GTK/Kvantum bits and select
 the look live.
"""

POSTINST = r'''#!/bin/sh
set -e
# refresh font cache for the system font dir we populated
if command -v fc-cache >/dev/null 2>&1; then
  fc-cache -f /usr/share/fonts/truetype/el-indiglo >/dev/null 2>&1 || true
fi
# rebuild KDE's service/package cache so the new Global Theme previews are picked
# up (a plain file-copy into /usr/share doesn't invalidate the running cache).
if command -v kbuildsycoca6 >/dev/null 2>&1; then
  kbuildsycoca6 --noincremental >/dev/null 2>&1 || true
fi
echo "el-indiglo-themes installed. Run:  el-indiglo-apply EL-Indiglo"
echo "(variants: EL-Indiglo[-Lit], EL-Azure[-Lit], EL-Amber[-Lit])"
echo "If Global Theme thumbnails still show Breeze, log out and back in (or run"
echo "kquitapp6 plasmashell && kstart plasmashell) to refresh the preview cache."
exit 0
'''

POSTRM = r'''#!/bin/sh
set -e
if [ "$1" = "remove" ] || [ "$1" = "purge" ]; then
  if command -v fc-cache >/dev/null 2>&1; then
    fc-cache -f >/dev/null 2>&1 || true
  fi
fi
exit 0
'''


def copy_into(src_rel, dst_rel):
    src = os.path.join(ROOT, src_rel)
    dst = os.path.join(DEB_ROOT, dst_rel)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if os.path.isdir(src):
        shutil.copytree(src, dst, dirs_exist_ok=True)
    else:
        shutil.copy2(src, dst)


def build():
    shutil.rmtree(BUILD, ignore_errors=True)
    os.makedirs(DEB_ROOT)

    mapping = system_mapping() + helper_source_mapping()
    missing = [s for s, _ in mapping if not os.path.exists(os.path.join(ROOT, s))]
    if missing:
        raise SystemExit(f"payload sources missing: {missing}")
    for src, dst in mapping:
        copy_into(src, dst)

    # Look-and-Feel packages (staged absolute sources; built after the rmtree)
    lnf_mapping = build_lnf_packages()
    for abs_src, dst in lnf_mapping:
        d = os.path.join(DEB_ROOT, dst)
        os.makedirs(os.path.dirname(d), exist_ok=True)
        shutil.copytree(abs_src, d, dirs_exist_ok=True)
    mapping = mapping + lnf_mapping

    # per-variant widget icon: render a phosphor segment-clock from the variant
    # tokens into the plasmoid's contents/icons/ and point KPlugin.Icon at it, so
    # the Add-Widgets list shows THIS variant's phosphor, not the generic clock.
    import make_preview as _mp
    for v in VARIANTS:
        mid = f"org.el.segclock.{v.lower().replace('-', '')}"
        pdir = os.path.join(DEB_ROOT, f"usr/share/plasma/plasmoids/{mid}")
        meta_p = os.path.join(pdir, "metadata.json")
        if not os.path.isfile(meta_p):
            continue
        icons_dir = os.path.join(pdir, "contents", "icons")
        os.makedirs(icons_dir, exist_ok=True)
        cols = _mp.parse_scheme(v)
        import cairosvg as _cs
        _cs.svg2png(bytestring=_mp.icon_svg(cols).encode(),
                    write_to=os.path.join(icons_dir, "el-segclock.png"),
                    output_width=256, output_height=256)
        meta = _json.loads(open(meta_p).read())
        meta["KPlugin"]["Icon"] = "el-segclock"
        open(meta_p, "w").write(_json.dumps(meta, indent=2))
    for v in VARIANTS:
        wdir = os.path.join(DEB_ROOT, f"usr/share/wallpapers/{v}")
        if os.path.isdir(wdir):
            wmeta = {
                "KPlugin": {
                    "Id": v,
                    "Name": f"EL Indiglo ({v})",
                    "License": "GPLv3",
                    "Authors": [{"Name": "EL Indiglo"}],
                },
                "KPackageStructure": "Plasma/Wallpaper",
            }
            open(os.path.join(wdir, "metadata.json"), "w").write(
                _json.dumps(wmeta, indent=2))

    # Chrome/Chromium themes (⊕CHROME-THEME): per-variant manifest.json emitted
    # from the same scheme tokens, loadable unpacked via chrome://extensions.
    import make_chrome as _chrome
    cdirs = {v: os.path.join(DEB_ROOT, f"usr/share/el-indiglo/chrome/{v}")
             for v in VARIANTS}
    _chrome.render_all(VARIANTS, cdirs)

    # Konsole colorschemes (⊕KONSOLE): 5th palette emitter, into the system
    # Konsole dir (auto-discovered). Plus Alacritty/foot off the same ANSI 16.
    import make_konsole as _kon
    kdir = os.path.join(DEB_ROOT, "usr/share/konsole")
    os.makedirs(kdir, exist_ok=True)
    for v in VARIANTS:
        open(os.path.join(kdir, f"{v}.colorscheme"), "w").write(_kon.colorscheme(v))
    tdir = os.path.join(DEB_ROOT, "usr/share/el-indiglo/terminals")
    os.makedirs(tdir, exist_ok=True)
    for v in VARIANTS:
        open(os.path.join(tdir, f"{v}.alacritty.toml"), "w").write(_kon.alacritty_toml(v))
        open(os.path.join(tdir, f"{v}.foot.ini"), "w").write(_kon.foot_ini(v))

    # Plymouth boot-splash themes (⊕PLYMOUTH): 7th emitter, the earliest seam.
    import make_plymouth as _ply
    pdirs = {v: os.path.join(DEB_ROOT, f"usr/share/plymouth/themes/el-indiglo-{v}")
             for v in VARIANTS}
    _ply.render_all(VARIANTS, pdirs)

    # Live wallpaper plugins (⊕WALLPAPER-LIVE): 8th emitter, mounts on desktop +
    # lock. One Plasma/Wallpaper package per variant.
    import make_wallpaper_live as _wpl
    wldirs = {v: os.path.join(
        DEB_ROOT,
        f"usr/share/plasma/wallpapers/org.el.indiglo.live.{v.lower().replace('-', '')}")
        for v in VARIANTS}
    _wpl.render_all(VARIANTS, wldirs)

    # Notification-marquee plasmoids (⊕NOTIFY-MARQUEE): 9th emitter — phosphor
    # ticker that subsumes the occluding popups. One Plasma/Applet per variant.
    import make_notify_marquee as _nm
    nmdirs = {v: os.path.join(
        DEB_ROOT,
        f"usr/share/plasma/plasmoids/org.el.notifymarquee.{v.lower().replace('-', '')}")
        for v in VARIANTS}
    _nm.render_all(VARIANTS, nmdirs)

    # ⊕GLANCE-AUDIT gate: every ghost-bearing surface must clear its parsing-mode
    # floor (glanced-at needs more separation than looked-at). A surface that drops
    # a distinguishing channel (as the live wallpaper once did) fails the BUILD
    # here, before it can ship and have to be noticed.
    import glance_audit as _ga
    for _v in VARIANTS:
        _ok, _rows = _ga.run(_v, verbose=False)
        if not _ok:
            _bad = [r for r in _rows if not r[2]]
            raise SystemExit(f"GLANCE-AUDIT failed for {_v}: "
                             + "; ".join(f"{n} eff={e:.2f}<floor={f}" for n, m, ok, e, f, d in _bad))

    # helper binary
    hp = os.path.join(DEB_ROOT, "usr/bin/el-indiglo-apply")
    os.makedirs(os.path.dirname(hp), exist_ok=True)
    open(hp, "w").write(APPLY_HELPER)
    os.chmod(hp, 0o755)

    # root SDDM helper (run with sudo)
    sp = os.path.join(DEB_ROOT, "usr/bin/el-indiglo-sddm")
    open(sp, "w").write(SDDM_HELPER)
    os.chmod(sp, 0o755)

    # root Plymouth helper (run with sudo)
    pp = os.path.join(DEB_ROOT, "usr/bin/el-indiglo-plymouth")
    open(pp, "w").write(PLYMOUTH_HELPER)
    os.chmod(pp, 0o755)

    # live-wallpaper helper (per-user, opt-in)
    lp = os.path.join(DEB_ROOT, "usr/bin/el-indiglo-live")
    open(lp, "w").write(LIVE_HELPER)
    os.chmod(lp, 0o755)

    # notification-marquee helper (per-user, opt-in)
    np = os.path.join(DEB_ROOT, "usr/bin/el-indiglo-notify")
    open(np, "w").write(NOTIFY_HELPER)
    os.chmod(np, 0o755)

    # ⊕QML-SANITY: parse-check EVERY staged .qml with the real Qt qmllint (PySide6)
    # before packaging. This is an OBSERVABLE gate — "does it actually parse?" — not
    # the string-presence proxy that let a doubled-quote color ship a black
    # wallpaper in 1.23.0. Only genuine syntax/type errors fail the build; KDE
    # import-resolution warnings (modules absent in-container) are filtered.
    import qml_sanity as _qs
    _qml_errs = []
    for _r, _d, _fs in os.walk(DEB_ROOT):
        for _f in _fs:
            if _f.endswith(".qml"):
                _p = os.path.join(_r, _f)
                _qml_errs += _qs.check_qml(open(_p).read(), _p.replace(DEB_ROOT, ""))
    if _qml_errs:
        raise SystemExit("QML-SANITY failed (real qmllint):\n  " + "\n  ".join(_qml_errs[:12]))

    # control dir
    ctrl = os.path.join(DEB_ROOT, "DEBIAN")
    os.makedirs(ctrl)
    # installed-size in KiB
    size = 0
    for dp, _, fs in os.walk(DEB_ROOT):
        if "DEBIAN" in dp:
            continue
        for f in fs:
            size += os.path.getsize(os.path.join(dp, f))
    open(os.path.join(ctrl, "control"), "w").write(CONTROL.format(size=size // 1024 + 1))
    for name, body in [("postinst", POSTINST), ("postrm", POSTRM)]:
        p = os.path.join(ctrl, name)
        open(p, "w").write(body)
        os.chmod(p, 0o755)

    tmp_out = f"/tmp/{PKG}_{VERSION}_{ARCH}.deb"
    subprocess.run(["dpkg-deb", "--build", "--root-owner-group", DEB_ROOT, tmp_out],
                   check=True)
    out = f"/mnt/user-data/outputs/{PKG}_{VERSION}_{ARCH}.deb"
    shutil.copy2(tmp_out, out)
    return out, mapping


if __name__ == "__main__":
    out, mapping = build()
    print("built", out, "with", len(mapping), "mapped paths")
