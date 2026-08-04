#!/usr/bin/env python3
"""Plymouth boot-splash emitter (⊕PLYMOUTH) — the EARLIEST + RICHEST seam.

Seventh palette emitter. Generates a per-variant Plymouth `script`-plugin theme:
phosphor seven-segment digit PNGs (lit + ghost) rendered from the SAME scheme
tokens as everything else, plus a <variant>.plymouth config and a <variant>.script
wiring the REAL Plymouth callbacks (fetched, session 49):

  - SetBootProgressFunction(duration, progress): STOPWATCH — the watch times the
    real boot (counts elapsed `duration`); segments warm ghost->lit with progress.
  - SetRefreshFunction(): 1-2 frame phosphor FADE on change + ~1Hz colon blink.
  - SetDisplayPasswordFunction(prompt, bullets): BACKLIGHT ON (attention mode) +
    a bullet per typed char — the Openglo button press when boot blocks on YOU.
  - SetMessageFunction / SetUpdateStatusFunction: status MARQUEE across the field.

Design honesty: no faked wall-clock (unsourceable that early). Elapsed time IS
sourceable, so the watch runs its STOPWATCH — the real thing it can do. Hue stays
the variant identity; lit/non-lit (backlight) is the orthogonal MODE channel.

The .script deliberately reuses idioms from real, shipping Plymouth themes
(arch-beat, basic, Rudd-O-Grey) — never a from-scratch renderer — since this
runs in the initramfs and can't be live-tested here (operator=other reboot).
"""
import os
from PIL import Image, ImageDraw
import make_preview as MP
import segment_topology as ST

ROOT = os.path.dirname(os.path.abspath(__file__))

# 7-seg segment set per digit (which of the coarse 7 segments are lit).
# coarse names: a(top) b(top-right) c(bot-right) d(bottom) e(bot-left) f(top-left) g(middle)
SEVENSEG = {
    "0": set("abcdef"), "1": set("bc"), "2": set("abdeg"), "3": set("abcdg"),
    "4": set("bcfg"), "5": set("acdfg"), "6": set("acdefg"), "7": set("abc"),
    "8": set("abcdefg"), "9": set("abcdfg"),
}
# coarse 7-seg -> GEOM16 strokes (2 wide x 4 tall grid; y down)
SEG_STROKE = {
    "a": ("h", 0, 2, 0), "g": ("h", 0, 2, 2), "d": ("h", 0, 2, 4),
    "f": ("v", 0, 0, 2), "b": ("v", 2, 0, 2),
    "e": ("v", 0, 2, 4), "c": ("v", 2, 2, 4),
}

CELL_W, CELL_H = 2.0, 4.0


def _rgb(hexstr):
    h = hexstr.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _draw_stroke(dr, spec, U, T, ox, oy, color):
    """Draw one segment stroke as a filled polygon (matches the clock QML)."""
    g = T * 0.6
    kind = spec[0]
    if kind == "h":
        a, b, y = spec[1] * U, spec[2] * U, spec[3] * U
        pts = [(a + g, y - T / 2), (b - g, y - T / 2), (b - g, y + T / 2), (a + g, y + T / 2)]
    else:  # v
        x, y0, y1 = spec[1] * U, spec[2] * U, spec[3] * U
        pts = [(x - T / 2, y0 + g), (x + T / 2, y0 + g), (x + T / 2, y1 - g), (x - T / 2, y1 - g)]
    dr.polygon([(ox + px, oy + py) for px, py in pts], fill=color)


def render_digit(ch, lit_rgb, ghost_rgb, U=48, weight=1.0, ghost=True):
    """Render a 7-seg digit (or blank) to an RGBA PNG image. Lit segments in
    lit_rgb; unlit in ghost_rgb (faint) when ghost=True."""
    W = int(CELL_W * U + U)
    H = int(CELL_H * U + U)
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dr = ImageDraw.Draw(img)
    ox, oy = U * 0.5, U * 0.5
    on = SEVENSEG.get(ch, set())
    T_lit = U * 0.32 * (1.0 + 0.25 * weight)
    T_gh = U * 0.32 * (1.0 - 0.19 * weight)
    for seg, spec in SEG_STROKE.items():
        if seg in on:
            _draw_stroke(dr, spec, U, T_lit, ox, oy, lit_rgb + (255,))
        elif ghost:
            _draw_stroke(dr, spec, U, T_gh, ox, oy, ghost_rgb + (int(255 * 0.5),))
    return img


def render_colon(lit_rgb, U=48, on=True):
    W = int(U * 0.8)
    H = int(CELL_H * U + U)
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dr = ImageDraw.Draw(img)
    r = U * 0.22
    cx = W / 2
    col = lit_rgb + (255,) if on else lit_rgb + (60,)
    for cy in (U * 1.4, U * 2.6):
        dr.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col)
    return img


def ghost_from(lit_rgb, ground_rgb):
    """Dim phosphor toward ground for the unlit segment tint (same model)."""
    return tuple(int(round(lit_rgb[i] + (ground_rgb[i] - lit_rgb[i]) * 0.6)) for i in range(3))


def render_assets(variant, out_dir, U=48):
    """Render all digit/colon PNGs (lit-on-void 'normal' set + backlit set) into
    out_dir. Returns the list of written files."""
    c = MP.parse_scheme(variant)
    ground = _rgb(c["ground"])
    phosphor = _rgb(c["phosphor"])
    gh = ghost_from(phosphor, ground)
    os.makedirs(out_dir, exist_ok=True)
    written = []
    # normal (dark display): phosphor-lit segments, ghost dim, transparent bg
    for d in list("0123456789"):
        p = os.path.join(out_dir, f"d{d}.png")
        render_digit(d, phosphor, gh, U=U).save(p)
        written.append(p)
    render_digit(" ", phosphor, gh, U=U).save(os.path.join(out_dir, "dblank.png"))
    written.append(os.path.join(out_dir, "dblank.png"))
    render_colon(phosphor, U=U, on=True).save(os.path.join(out_dir, "colon_on.png"))
    render_colon(phosphor, U=U, on=False).save(os.path.join(out_dir, "colon_off.png"))
    written += [os.path.join(out_dir, "colon_on.png"), os.path.join(out_dir, "colon_off.png")]
    return written


def dot_theme(variant):
    """The .plymouth config (INI). ModuleName=script points at <variant>.script."""
    return (
        "[Plymouth Theme]\n"
        f"Name=EL Openglo ({variant})\n"
        f"Description=Electroluminescent watch boot splash — {variant}\n"
        "ModuleName=script\n\n"
        "[script]\n"
        f"ImageDir=/usr/share/plymouth/themes/el-openglo-{variant}\n"
        f"ScriptFile=/usr/share/plymouth/themes/el-openglo-{variant}/el-openglo.script\n"
    )


def script(variant):
    """The reactive .script. Reuses shipping-theme idioms (arch-beat / basic /
    Rudd-O-Grey) for progress/message/password/refresh callbacks."""
    c = MP.parse_scheme(variant)
    gr, gg, gb = _rgb(c["ground"])
    pr, pg, pb = tuple(v / 255.0 for v in _rgb(c["phosphor"]))
    return f'''# EL Openglo Plymouth theme ({variant}) — reactive phosphor watch.
# Generated by make_plymouth.py from the scheme tokens (do not hand-edit).

# --- void ground -----------------------------------------------------------
Window.SetBackgroundTopColor ({gr/255.0}, {gg/255.0}, {gb/255.0});
Window.SetBackgroundBottomColor ({gr/255.0}, {gg/255.0}, {gb/255.0});

sw = Window.GetWidth ();
sh = Window.GetHeight ();

# --- digit assets ----------------------------------------------------------
for (i = 0; i < 10; i++)
    digit_image[i] = Image ("d" + i + ".png");
blank_image = Image ("dblank.png");
colon_on = Image ("colon_on.png");
colon_off = Image ("colon_off.png");

dw = digit_image[0].GetWidth ();
dh = digit_image[0].GetHeight ();
# stopwatch layout: M : S S  (4 digit slots + colon), centred
group_w = dw * 4 + colon_on.GetWidth ();
base_x = sw / 2 - group_w / 2;
base_y = sh / 2 - dh / 2;

for (i = 0; i < 4; i++) {{
    slot[i].sprite = Sprite ();
    slot[i].sprite.SetImage (blank_image);
    xoff = i * dw;
    if (i >= 1) xoff = xoff + colon_on.GetWidth ();   # gap for the colon
    slot[i].sprite.SetX (base_x + xoff);
    slot[i].sprite.SetY (base_y);
    slot[i].sprite.SetZ (10);
    slot[i].value = -1;
}}
colon.sprite = Sprite (colon_on);
colon.sprite.SetX (base_x + dw);
colon.sprite.SetY (base_y);
colon.sprite.SetZ (10);

fun set_slot (i, ch) {{
    if (slot[i].value == ch) return;         # phosphor fade only on change
    slot[i].value = ch;
    if (ch < 0) slot[i].sprite.SetImage (blank_image);
    else slot[i].sprite.SetImage (digit_image[ch]);
    slot[i].fade = 1.0;                       # kick a short fade-in
}}

# --- state -----------------------------------------------------------------
global.progress = 0;
global.elapsed = 0;
global.tick = 0;
global.blocked = 0;      # backlight (attention) when waiting on the user
global.bullets = 0;
global.status = "";

# --- STOPWATCH + progress warm (SetBootProgressFunction) -------------------
fun on_progress (duration, progress) {{
    global.elapsed = duration;
    global.progress = progress;
    # render elapsed seconds as M:SS on the four slots
    total = Math.Int (duration);
    mins = Math.Int (total / 60);
    secs = total - mins * 60;
    set_slot (0, Math.Int (mins % 10));
    set_slot (1, Math.Int (secs / 10));
    set_slot (2, Math.Int (secs % 10));
    set_slot (3, -1);
}}
Plymouth.SetBootProgressFunction (on_progress);

# --- refresh: phosphor fade + ~1Hz colon blink + status marquee -----------
# (Plymouth allows ONE refresh callback — all per-frame work lives here.)
fun on_refresh () {{
    global.tick++;
    # colon blink ~1Hz (50 refreshes/sec -> toggle every 25)
    if (Math.Int (global.tick / 25) % 2 == 0)
        colon.sprite.SetImage (colon_on);
    else
        colon.sprite.SetImage (colon_off);
    # 1-2 frame phosphor fade: ramp opacity up quickly after a change
    for (i = 0; i < 4; i++) {{
        if (slot[i].fade > 0) {{
            slot[i].fade = slot[i].fade - 0.5;    # ~2 frames
            op = 1.0 - slot[i].fade * 0.5;
            slot[i].sprite.SetOpacity (op);
        }} else {{
            slot[i].sprite.SetOpacity (1.0);
        }}
    }}
    # status marquee: scroll the message left across the field
    if (global.status != "") {{
        message.x = message.x - 3;
        if (message.image) {{
            if (message.x < 0 - message.image.GetWidth ()) message.x = sw;
            message.sprite.SetX (message.x);
        }}
    }}
}}
Plymouth.SetRefreshFunction (on_refresh);

# --- BACKLIGHT ON when blocked on user input (password) --------------------
# The Openglo button: when boot waits for YOU, light the field + a bullet/char.
fun on_password (prompt, bullets) {{
    global.blocked = 1;
    global.bullets = bullets;
    # backlight: raise the ground toward a lit field (attention mode)
    Window.SetBackgroundTopColor ({min(1.0, pr*0.5)}, {min(1.0, pg*0.5)}, {min(1.0, pb*0.5)});
    Window.SetBackgroundBottomColor ({min(1.0, pr*0.35)}, {min(1.0, pg*0.35)}, {min(1.0, pb*0.35)});
    # show a bullet per typed char across the slots (segments light as you type)
    for (i = 0; i < 4; i++) {{
        if (i < bullets) set_slot (i, 8);        # '8' = all segments = a filled cell
        else set_slot (i, -1);
    }}
}}
Plymouth.SetDisplayPasswordFunction (on_password);

fun on_normal () {{
    global.blocked = 0;
    Window.SetBackgroundTopColor ({gr/255.0}, {gg/255.0}, {gb/255.0});
    Window.SetBackgroundBottomColor ({gr/255.0}, {gg/255.0}, {gb/255.0});
}}
Plymouth.SetDisplayNormalFunction (on_normal);

# --- status source (SetMessage / SetUpdateStatus feed the marquee) ---------
message.sprite = Sprite ();
message.x = 0;
fun show_message (text) {{
    global.status = text;
    message.image = Image.Text (text, {pr}, {pg}, {pb});
    message.sprite.SetImage (message.image);
    message.sprite.SetY (base_y + dh + dh * 0.4);
    message.x = sw;                              # start off the right edge
}}
fun on_message (text) {{ show_message (text); }}
Plymouth.SetMessageFunction (on_message);
Plymouth.SetUpdateStatusFunction (on_message);
'''


def render_all(variants, dir_map):
    written = {}
    for v in variants:
        d = dir_map[v]
        files = render_assets(v, d)
        open(os.path.join(d, "el-openglo.plymouth"), "w").write(dot_theme(v))
        open(os.path.join(d, "el-openglo.script"), "w").write(script(v))
        written[v] = files + [os.path.join(d, "el-openglo.plymouth"),
                              os.path.join(d, "el-openglo.script")]
    return written


if __name__ == "__main__":
    variants = ["EL-Openglo", "EL-Openglo-Lit", "EL-Azure", "EL-Azure-Lit",
                "EL-Amber", "EL-Amber-Lit"]
    outs = {v: f"/tmp/ply-{v}" for v in variants}
    w = render_all(variants, outs)
    print("rendered", len(w), "Plymouth themes")
    for v in variants:
        print(" ", v, "->", len(w[v]), "files")
