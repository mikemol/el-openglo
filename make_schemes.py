#!/usr/bin/env python3
"""EL scheme generator: the knob, for the whole theme.

Emits KDE .colors and Konsole .colorscheme files for every cell of the grid
    phosphor {openglo, azure, amber} x mode {off, lit}
from per-variant token tables. 'off' = backlight off (EL segments illuminate a
black panel); 'lit' = backlight on (dark LCD occludes the glowing panel).

Run: python3 make_schemes.py [--verify]
--verify additionally diffs regenerated output against the original hand-made
.colors files (must be byte-identical) and runs a WCAG contrast audit.
"""
import sys, os

# ---------------------------------------------------------------- token tables
# Each variant: ~30 base tokens; the emitter expands them to every INI slot.
# Semantic rule: negative/neutral/positive keep meaning everywhere, but shift
# hue/value when they'd collide with the phosphor field (amber) or lose
# contrast against it (lit modes).

IND_OFF = dict(
  name="EL Openglo", id="EL-Openglo",
  view="6,11,13", view_alt="10,18,20", window="12,21,23", window_alt="10,19,21",
  button="18,34,37", button_alt="16,30,33", header="8,16,18", header_alt="10,18,20",
  hdr_in_bg="6,11,13", hdr_in_alt="8,14,16", comp="6,11,13", comp_alt="8,14,16",
  tt_bg="10,18,20", tt_alt="8,14,16",
  fg="140,232,218", fg_act="168,255,242", fg_in="61,102,96",
  link="69,216,240", visited="58,151,166",
  neg="255,110,99", neu="255,180,84", pos="85,240,160",
  focus="0,224,194", hover="26,165,147",
  sel_bg="0,205,176", sel_alt="0,180,155", sel_fg="4,33,29", sel_in="10,64,56",
  sel_link="6,58,84", sel_vis="12,66,74",
  sel_neg="120,26,20", sel_neu="110,66,8", sel_pos="8,74,40",
  fx_dis="6,11,13", fx_in="8,14,16",
  tt_is_sel=False,
)

AZR_OFF = dict(
  name="EL Azure", id="EL-Azure",
  view="5,9,14", view_alt="9,16,24", window="11,19,27", window_alt="9,17,25",
  button="18,28,42", button_alt="16,26,38", header="7,14,22", header_alt="9,16,24",
  hdr_in_bg="5,9,14", hdr_in_alt="7,12,19", comp="5,9,14", comp_alt="7,12,19",
  tt_bg="9,16,24", tt_alt="7,12,19",
  fg="138,196,242", fg_act="169,220,255", fg_in="61,85,102",
  link="79,227,232", visited="58,127,166",
  neg="255,110,99", neu="255,180,84", pos="85,240,160",
  focus="79,168,255", hover="42,111,184",
  sel_bg="61,155,240", sel_alt="52,133,210", sel_fg="4,20,35", sel_in="10,44,70",
  sel_link="12,52,92", sel_vis="14,54,88",
  sel_neg="120,26,20", sel_neu="110,66,8", sel_pos="8,74,40",
  fx_dis="5,9,14", fx_in="7,12,19",
  tt_is_sel=False,
)

AMB_OFF = dict(
  name="EL Amber", id="EL-Amber",
  view="10,7,4", view_alt="20,16,9", window="23,18,11", window_alt="21,17,10",
  button="37,29,16", button_alt="33,26,15", header="18,14,8", header_alt="20,16,9",
  hdr_in_bg="10,7,4", hdr_in_alt="16,12,7", comp="10,7,4", comp_alt="16,12,7",
  tt_bg="20,16,9", tt_alt="16,12,7",
  fg="232,196,140", fg_act="255,226,168", fg_in="102,87,61",
  link="111,216,232", visited="90,150,160",          # functional cold color
  neg="255,110,99", neu="255,235,110", pos="85,240,160",  # neutral de-collided
  focus="255,162,61", hover="184,116,40",
  sel_bg="217,154,40", sel_alt="190,133,32", sel_fg="33,23,6", sel_in="70,50,14",
  sel_link="10,70,84", sel_vis="20,60,66",
  sel_neg="120,26,20", sel_neu="92,74,6", sel_pos="8,74,40",
  fx_dis="10,7,4", fx_in="16,12,7",
  tt_is_sel=False,
)

IND_LIT = dict(
  name="EL Openglo Lit", id="EL-Openglo-Lit",
  view="175,242,226", view_alt="160,235,218", window="157,230,213", window_alt="147,222,204",
  button="138,218,203", button_alt="126,208,192", header="147,222,204", header_alt="160,235,218",
  hdr_in_bg="196,237,228", hdr_in_alt="196,237,228", comp=None, comp_alt=None,
  tt_bg="11,31,28", tt_alt="8,24,21",
  fg="10,38,34", fg_act="3,27,23", fg_in="78,138,128",
  link="6,106,138", visited="42,106,116",
  neg="166,35,24", neu="138,90,10", pos="7,102,53",
  focus="0,112,95", hover="14,138,118",
  sel_bg="11,31,28", sel_alt="8,24,21", sel_fg="124,243,223", sel_in="78,138,128",
  sel_link="124,232,255", sel_vis="140,200,210",
  sel_neg="255,154,140", sel_neu="255,204,133", sel_pos="140,247,190",
  sel_focus="0,224,194", sel_hover="26,165,147",     # dark-mode glow on the sel panel
  fx_dis="175,242,226", fx_in="196,237,228",
  tt_is_sel=True,
)

AZR_LIT = dict(
  name="EL Azure Lit", id="EL-Azure-Lit",
  view="178,220,250", view_alt="165,210,244", window="160,206,240", window_alt="150,196,232",
  button="140,188,226", button_alt="128,176,216", header="150,196,232", header_alt="165,210,244",
  hdr_in_bg="198,228,248", hdr_in_alt="198,228,248", comp=None, comp_alt=None,
  tt_bg="8,18,30", tt_alt="6,14,24",
  fg="10,26,42", fg_act="3,17,31", fg_in="74,110,140",
  link="6,120,138", visited="42,96,120",
  neg="166,35,24", neu="138,90,10", pos="7,102,53",
  focus="20,90,170", hover="28,110,190",
  sel_bg="8,18,30", sel_alt="6,14,24", sel_fg="133,203,255", sel_in="74,110,140",
  sel_link="124,240,255", sel_vis="150,196,220",
  sel_neg="255,154,140", sel_neu="255,204,133", sel_pos="140,247,190",
  sel_focus="79,168,255", sel_hover="42,111,184",
  fx_dis="178,220,250", fx_in="198,228,248",
  tt_is_sel=True,
)

AMB_LIT = dict(
  name="EL Amber Lit", id="EL-Amber-Lit",
  view="250,220,160", view_alt="242,208,142", window="238,204,138", window_alt="228,192,124",
  button="218,182,116", button_alt="205,170,105", header="228,192,124", header_alt="242,208,142",
  hdr_in_bg="250,232,196", hdr_in_alt="250,232,196", comp=None, comp_alt=None,
  tt_bg="33,23,6", tt_alt="26,18,5",
  fg="42,30,8", fg_act="30,20,4", fg_in="140,114,70",
  link="8,105,120", visited="50,95,105",
  neg="150,30,20", neu="108,86,6", pos="6,95,48",
  focus="150,92,10", hover="176,110,16",
  sel_bg="33,23,6", sel_alt="26,18,5", sel_fg="255,206,117", sel_in="140,114,70",
  sel_link="140,235,250", sel_vis="200,180,140",
  sel_neg="255,154,140", sel_neu="255,240,150", sel_pos="140,247,190",
  sel_focus="255,162,61", sel_hover="184,116,40",
  fx_dis="250,220,160", fx_in="250,232,196",
  tt_is_sel=True,
)

import os as _os
# ⊕PARAMETRIC-PALETTE: when USE_SOLVER=1, the GRID is DERIVED by solving each
# token against its constraint (make_palette), instead of the authored table
# below. The authored GRID is kept as residue (the shadow-engineer loop) and is
# the default until the solved palette is live-validated (operator=other). Flip
# the flag to re-solve every token from (hue seed x thresholds) — e.g. a
# WCAG->APCA threshold change becomes a one-line edit, not hand-chasing colors.
# ⚑ RECOVERY REPAIR (2 of 2).  A THIRD copy of the solver-flag block stood here,
# BEFORE _AUTHORED_GRID is defined, so importing this module raised NameError —
# its own comment ("defined just below") admits the forward reference.  The
# transcript replay left three near-duplicate copies of this block; the two that
# remain both sit AFTER the table, and the last is the canonical form.  Removing
# the premature copy is the whole fix: USE_SOLVER is re-read there anyway.
#
# ⚑ THIS IS WHY `** PARTIAL **` IS A LOAD-BEARING WARNING.  The file compiles
# clean — a forward reference is only an error at RUN time — so check_compiles
# passed it, and nothing imported it until a generator was actually executed.

# ⚑ RECOVERY REPAIR (1 of 2).  The archive had this defined as `_AUTHORED__AUTHORED_GRID`
# — a doubled prefix left by a transcript-replay str_replace whose anchor text
# mismatched.  It is what `** PARTIAL **` meant for this file: it BYTE-COMPILES
# (the name is valid) and fails at import, which is why compiling is too weak a
# witness for a partial file.  The three reference sites all say `_AUTHORED_GRID`,
# so the intended name is unambiguous.
_AUTHORED_GRID = {  # (phosphor, mode) -> (tokens, dark-counterpart for Complementary)
  ("openglo","off"): (IND_OFF, IND_OFF), ("openglo","lit"): (IND_LIT, IND_OFF),
  ("azure","off"):   (AZR_OFF, AZR_OFF), ("azure","lit"):   (AZR_LIT, AZR_OFF),
  ("amber","off"):   (AMB_OFF, AMB_OFF), ("amber","lit"):   (AMB_LIT, AMB_OFF),
}

import os as _os
# ⊕PARAMETRIC-PALETTE / ⊕SOLVER-DEFAULT — UNBLOCKED, and the default is SOLVED.
#
# ⚑ THIS COMMENT SAID "BLOCKED" LONG AFTER IT WASN'T.  It described the solver as
# handling only the 4 display primitives while the ~5 semantic tokens still failed
# the hue-sector and distinctness gates — true once, and the log records the two
# closures that ended it: ⊕SOLVER-SEMANTIC (the joint constellation solver) and
# ⊕SOLVER-BACKLIT-CVD (widened candidates + the objective re-pointed at the gate's
# own normalized-q), after which ⊕SOLVER-DEFAULT was FLIPPED and all six variants
# solve clean. The comment outlived every one of those.
#
# It is worth naming what that cost: the stale text sat directly above the code it
# contradicted, and it argued for exactly the inverted default the recovery had
# left behind — so anyone reading to check the polarity found a rationale for the
# wrong answer. A comment is not inert; a stale one actively defends the bug.
# ⚑ RECOVERY REPAIR (3 of 3): THE SOLVER DEFAULT WAS INVERTED *AND* DUPLICATED.
#
# Two near-identical blocks stood here, gated on DIFFERENT env vars — EL_SOLVER
# then USE_SOLVER — and the second silently overwrote the first. So `EL_SOLVER=1`
# re-solved the whole palette and then threw the result away: the emitted schemes
# were always the authored fallback, and no error was raised. That is the
# washed-out palette the audit set out to explain, and it is invisible from the
# outside because a fallback palette is a perfectly valid one — just not the
# solved one.
#
# The design log settles the polarity (⊕SOLVER-DEFAULT, FLIPPED): once all six
# variants solved clean, the SOLVED palette became the default and the authored
# table was kept as residue behind EL_AUTHORED_PALETTE=1. The recovered file had
# it backwards. Reachability is the reason it matters: the user installs from the
# .deb, so a palette reachable only via an env var nobody sets is not shipped.
#
# ⚑ THE FALLBACK STILL EXISTS AND IS STILL NAMED. Keeping _AUTHORED_GRID is not
# hedging — it is the residue the shadow-engineer loop requires, and it is what
# makes `EL_AUTHORED_PALETTE=1` a one-line A/B against the solver.
#
# ⚑ AND THE SOLVE IS CACHED, BECAUSE IT RUNS AT IMPORT TIME.  build_grid() is a
# multi-restart hillclimb over six variants — measured at ~108s — and this line
# is module-level, so EVERY importer paid it just to read GRID. A two-minute
# import turns any gate that touches the colour chain into a timeout, which is
# how a check gets quietly removed for being "flaky" instead of fixed.
#
# The cache is keyed by the inputs that can change the answer (the solver source
# and its threshold authority), so editing either invalidates it automatically.
# Delete .palette-cache.json, or set EL_NO_PALETTE_CACHE=1, to force a re-solve.
def _solved_grid():
    import hashlib
    import json
    import make_palette as _mp

    cache = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)),
                          ".palette-cache.json")
    key = hashlib.sha256()
    for dep in ("make_palette.py", "cvd_gate.py", "ghost_solve.py", "glance_audit.py"):
        p = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), dep)
        try:
            key.update(open(p, "rb").read())
        except OSError:
            key.update(b"<absent>")
    stamp = key.hexdigest()
    return _cached_solve(cache, stamp, _mp.build_grid,
                         use_cache=_os.environ.get("EL_NO_PALETTE_CACHE") != "1")


def _read_cache(cache, stamp):
    """The cached grid if `cache` holds one stamped `stamp`, else None."""
    import json
    try:
        with open(cache, encoding="utf-8") as fh:
            blob = json.load(fh)
        if blob.get("stamp") == stamp:
            # JSON has no tuple keys; the grid is keyed (phosphor, mode).
            return {tuple(k.split("\t")): v for k, v in blob["grid"].items()}
    except (OSError, ValueError, KeyError, AttributeError):
        pass
    return None


def _cached_solve(cache, stamp, solve, use_cache=True):
    """Return the grid for `stamp`: from `cache` if it holds it, else `solve()`.

    ⚑ THE SOLVE IS SERIALISED ACROSS PROCESSES (W68, 2026-09-22). The atomic write
    below stops a reader seeing a torn file, but nothing stopped N parallel checks
    on a cold cache from each running the full solve — N x ~108 s CPU, each under
    paperkit's per-check RLIMIT_CPU cap. An exclusive fcntl.flock on a sidecar
    `<cache>.lock` makes one process solve while the rest block, and the lock is
    DOUBLE-CHECKED: a waiter re-reads the cache after acquiring it, finds the
    winner's result, and returns without solving.

    ⚑ A DEAD HOLDER CANNOT DEADLOCK THIS. flock locks belong to the open file
    description, which the kernel closes when the process exits for ANY reason —
    SIGKILL, SIGXCPU from the RLIMIT_CPU cap, a core dump. The next waiter then
    acquires, re-reads (finds no fresh cache), and solves itself.

    ⚑ WAITING IS NOT CPU. A process blocked in flock() is asleep in the kernel and
    accrues no user or sys time, so it spends none of its RLIMIT_CPU budget while
    the winner solves. It DOES accrue wall time: a per-check WALL timeout (if a
    runner imposes one) still sees a waiter take as long as the solve. The winner's
    own solve is charged to the winner alone, exactly as before.

    WEAKNESSES, stated: (1) flock is advisory — a process that writes the cache
    without taking the lock (an older checkout of this file) is not excluded; the
    atomic replace still keeps its write whole. (2) flock over NFS is emulated or
    absent on some kernels/mounts; on such a filesystem the lock may not exclude
    across hosts. (3) If the lock file cannot be opened (read-only dir), this
    degrades to the old unserialised behaviour rather than failing — the cache is
    an optimisation. (4) With use_cache False (EL_NO_PALETTE_CACHE=1) every caller
    solves; the lock still serialises them, one after another, by design: that
    flag asks for a re-solve and gets one.
    """
    if use_cache:
        grid = _read_cache(cache, stamp)
        if grid is not None:
            return grid                        # fast path: no lock taken

    lock_fh = None
    try:
        import fcntl
        lock_fh = open(cache + ".lock", "a")
        fcntl.flock(lock_fh.fileno(), fcntl.LOCK_EX)   # blocks; sleeping, not CPU
    except (OSError, ImportError):
        if lock_fh is not None:
            lock_fh.close()
        lock_fh = None                         # weakness (3): proceed unlocked
    try:
        if use_cache:
            grid = _read_cache(cache, stamp)   # double-check: a winner may have solved
            if grid is not None:
                return grid
        grid = solve()
        _write_cache(cache, stamp, grid)
        return grid
    finally:
        if lock_fh is not None:
            lock_fh.close()                    # closing the fd releases the flock


def _write_cache(cache, stamp, grid):
    import json
    # ⚑ THE CACHE IS REPLACED, NEVER TRUNCATED IN PLACE (W68, 2026-09-22). The
    # previous form was `json.dump(..., open(cache, "w"))`, which TRUNCATES the
    # file and then writes it — so a concurrent reader sees a partial document.
    # paperkit grades the claim graph in PARALLEL and nine of its checks read this
    # palette, so several processes are in here at once by construction.
    #
    # ⚑ IT WAS HARMLESS AND IT WAS STILL WRONG. The reader catches OSError,
    # ValueError and KeyError and falls through to a full solve, so a torn cache
    # cost TIME, not correctness — which is exactly why it could sit here
    # unnoticed. A write that is only safe because every reader happens to be
    # forgiving is a coupling nobody declared, and the next reader need not be.
    # os.replace is atomic within a filesystem, so a reader sees the old file or
    # the new one and never a half of either.
    #
    # ⚑ THIS IS NOT CLAIMED AS THE CAUSE OF W68. Eleven checks failed once and
    # passed twice with no account captured; this was found while looking, and
    # fixing it is correct whether or not it was implicated.
    try:
        import tempfile
        fd, tmp = tempfile.mkstemp(dir=_os.path.dirname(cache), prefix=".palette-cache.")
        try:
            with _os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump({"stamp": stamp,
                           "grid": {"\t".join(k): v for k, v in grid.items()}}, fh)
            # ⚑ mkstemp CREATES 0600 AND open() DOES NOT — measured 2026-09-22, the
            # first cut of this repair silently turned a -rw-rw-r-- cache into a
            # -rw------- one. On a shared box that is a different artifact, and
            # nothing would have reported it: the cache is an optimisation, so a
            # reader that cannot open it just re-solves and stays green. Restore
            # the mode open() would have given, from this process's umask.
            _umask = _os.umask(0)
            _os.umask(_umask)
            _os.chmod(tmp, 0o666 & ~_umask)
            _os.replace(tmp, cache)
        except BaseException:
            _os.unlink(tmp)                     # never leave a partial beside the real one
            raise
    except OSError:
        pass                                    # a cache we cannot write is not an error


def _selftest_worker(cache, stamp, counter, delay):
    """One contender: a stub solve that records it ran and sleeps `delay` s."""
    import time
    def stub():
        with open(counter, "a") as fh:
            fh.write(f"{_os.getpid()}\n")
        time.sleep(delay)
        return {("stub", "off"): [{"view": "0,0,0"}, {"view": "0,0,0"}]}
    grid = _cached_solve(cache, stamp, stub)
    assert ("stub", "off") in grid


def _selftest():
    """Prove the lock SERIALISES: N forked contenders on a cold temp cache, one
    stubbed solve. The no-lock arm (lock path made unopenable) must show >1 solve,
    so the locked arm's 1 is a measurement and not the only possible output."""
    import multiprocessing, tempfile
    ctx = multiprocessing.get_context("fork")
    n = 4
    results = []
    for arm in ("locked", "unlocked"):
        with tempfile.TemporaryDirectory() as d:
            cache = _os.path.join(d, "cache.json")
            counter = _os.path.join(d, "solves")
            open(counter, "w").close()
            if arm == "unlocked":
                _os.mkdir(cache + ".lock")     # open(..., "a") on a dir -> OSError
            procs = [ctx.Process(target=_selftest_worker,
                                 args=(cache, "S", counter, 0.5)) for _ in range(n)]
            for p in procs: p.start()
            for p in procs: p.join()
            solves = len(open(counter).read().split())
            ok_exit = sum(p.exitcode == 0 for p in procs)
            results.append((arm, solves, ok_exit))
            print(f"  {arm:8s}: {solves} solve(s) over {n} contenders, "
                  f"{ok_exit} of {n} exited 0")
    (_, s_l, e_l), (_, s_u, e_u) = results
    good = s_l == 1 and e_l == n and s_u > 1 and e_u == n
    print("make_schemes selftest:", "PASS" if good else "FAIL")
    return 0 if good else 1


if _os.environ.get("EL_AUTHORED_PALETTE") == "1":
    GRID = _AUTHORED_GRID
else:
    GRID = _solved_grid()


# ⚑ THE GHOST'S RENDER ALPHA IS SOLVED HERE AND EMITTED, NOT HELD IN THE QML.
# SegmentChar.qml:73 carried `opacity: 0.45` as a constant no colour check could
# see, and at 0.45 three of the six variants cannot clear the ghost floor by ANY
# choice of fg_in (measured: check_ghost_composite.py --solve, a_min 0.49-0.51 on
# the Lit variants). Colour, alpha and width are one subordination quantity; the
# one of the three that was authored is now the one that is solved.  Operator
# ruling 2026-09-20: ONE global alpha, the max of the per-variant minima, so every
# variant keeps room for its colour solve.  Consumers read THIS; palette_graph's
# GHOST_ALPHA remains the record of what the renderer draws until it reads this.
def _ghost_alpha():
    """The grid's ghost alpha — READ from the emitted tokens, never re-solved here.

    ⚑ ONE SOLVE, ONE VALUE. `make_palette.build_grid` solves alpha once and stamps
    it on every token dict as `ghost_alpha`, and `fg_in` was solved THROUGH it. A
    second solve here could only agree by luck or disagree silently, so this reads
    the carried value and REFUSES if the variants do not all carry the same one.
    The authored fallback grid predates the field and gets the value its ghosts
    were drawn at, 0.45, recorded as such."""
    seen = set()
    for value in GRID.values():
        t = value[0] if isinstance(value, (list, tuple)) else value
        if isinstance(t, dict) and "view" in t:
            seen.add(t.get("ghost_alpha", "0.45"))
    if len(seen) != 1:
        raise ValueError(f"GRID carries {len(seen)} distinct ghost_alpha values "
                         f"{sorted(seen)}; the grid-wide solve did not happen")
    return float(seen.pop())


GHOST_ALPHA = _ghost_alpha()

# ---------------------------------------------------------------- .colors emit
def fgset(t):
    return (t["fg_act"], t["fg_in"], t["link"], t["neg"], t["neu"],
            t["fg"], t["pos"], t["visited"])

def section(title, bg_alt, bg, focus, hover, fgs, fg_normal_override=None):
    a, i, l, n, u, f, p, v = fgs
    if fg_normal_override: f = fg_normal_override
    return (f"[{title}]\n"
            f"BackgroundAlternate={bg_alt}\nBackgroundNormal={bg}\n"
            f"DecorationFocus={focus}\nDecorationHover={hover}\n"
            f"ForegroundActive={a}\nForegroundInactive={i}\nForegroundLink={l}\n"
            f"ForegroundNegative={n}\nForegroundNeutral={u}\nForegroundNormal={f}\n"
            f"ForegroundPositive={p}\nForegroundVisited={v}\n")

def emit_colors(t, dark):
    # ⚑ THE SELECTION GROUP IS THE ONE PLACE THE PALETTE INVERTS, so it is the one
    # place a BODY token is the wrong answer.  The active slot here was `fg_act` —
    # the body's hot-glow, chosen to sit on the dark ground — while every other
    # slot in this tuple is a `sel_*` token chosen to sit on the LIT selection
    # background.  Measured across all six variants, that put ForegroundActive at
    # 1.00:1 against its own background: text exactly the colour it is drawn on.
    #
    # `sel_act` is the selection's own active foreground, defaulting to `sel_fg`
    # (the slot proven legible on this background, 7.2:1-14.3:1) so a variant that
    # does not distinguish active-vs-normal in the inverted group stays readable
    # rather than invisible.
    sel_act = t.get("sel_act", t["sel_fg"])
    selfgs = (sel_act, t["sel_in"], t["sel_link"], t["sel_neg"],
              t["sel_neu"], t["sel_fg"], t["sel_pos"], t["sel_vis"])
    sf = t.get("sel_focus", t["focus"]); sh = t.get("sel_hover", t["hover"])
    ttfgs = selfgs if t["tt_is_sel"] else fgset(t)
    ttf, tth = (sf, sh) if t["tt_is_sel"] else (t["focus"], t["hover"])
    comp, comp_alt = (t["comp"] or dark["comp"]), (t["comp_alt"] or dark["comp_alt"])
    parts = [
      "[ColorEffects:Disabled]\n"
      f"Color={t['fx_dis']}\nColorAmount=0.35\nColorEffect=2\nContrastAmount=0.6\n"
      "ContrastEffect=1\nIntensityAmount=-1\nIntensityEffect=0\n",
      "[ColorEffects:Inactive]\nChangeSelectionColor=true\n"
      f"Color={t['fx_in']}\nColorAmount=0.2\nColorEffect=2\nContrastAmount=0.25\n"
      "ContrastEffect=2\nEnable=true\nIntensityAmount=0\nIntensityEffect=0\n",
      section("Colors:Button", t["button_alt"], t["button"], t["focus"], t["hover"], fgset(t)),
      section("Colors:Complementary", comp_alt, comp, dark["focus"], dark["hover"], fgset(dark)),
      section("Colors:Header", t["header_alt"], t["header"], t["focus"], t["hover"], fgset(t)),
      section("Colors:Header][Inactive", t["hdr_in_alt"], t["hdr_in_bg"], t["focus"],
              t["hover"], fgset(t), fg_normal_override=t["fg_in"]),
      section("Colors:Selection", t["sel_alt"], t["sel_bg"], sf, sh, selfgs),
      section("Colors:Tooltip", t["tt_alt"], t["tt_bg"], ttf, tth, ttfgs),
      section("Colors:View", t["view_alt"], t["view"], t["focus"], t["hover"], fgset(t)),
      section("Colors:Window", t["window_alt"], t["window"], t["focus"], t["hover"], fgset(t)),
      f"[General]\nColorScheme={t['id']}\nName={t['name']}\nshadeSortColumn=true\n",
      "[KDE]\ncontrast=4\n",
      f"[WM]\nactiveBackground={t['window']}\nactiveBlend={t['focus']}\n"
      f"activeForeground={t['fg_act']}\n"
      f"inactiveBackground={t['hdr_in_bg'] if t['tt_is_sel'] else t['view']}\n"
      f"inactiveBlend={t['fg_in']}\ninactiveForeground={t['fg_in']}\n",
      # ⚑ THE GHOST'S RENDER ALPHA TRAVELS WITH THE SCHEME.  KDE ignores an
      # unknown section, so this costs nothing there; make_preview.parse_scheme
      # reads it, which is how the surfaces that source from the .colors file
      # (plymouth) draw the ghost the palette solved — fg_in was solved to be
      # seen THROUGH this number, and a .colors file without it carries a colour
      # whose meaning depends on a value it does not state.
      # Two alphas since W12: looked-at (the clock) and glanced-at (surfaces you
      # only glance at — wallpaper, splash, plymouth — where the ghost must sit
      # further from lit). A variant that cannot satisfy both floors says so.
      f"[EL]\nGhostAlpha={t.get('ghost_alpha', '0.45')}\n"
      f"GhostAlphaGlanced={t.get('ghost_alpha_glanced', t.get('ghost_alpha', '0.45'))}\n"
      f"GhostAlphaGlancedInfeasible={t.get('ghost_alpha_glanced_infeasible', 'false')}\n",
    ]
    return "\n".join(parts)

# ------------------------------------------------------------- konsole emit
def rgb(s): return tuple(int(x) for x in s.split(","))
def mix(a, b, k): return tuple(round(x + (y - x) * k) for x, y in zip(rgb(a) if isinstance(a,str) else a, rgb(b) if isinstance(b,str) else b))
def s3(c): return ",".join(map(str, c))

ANSI = {  # variant id -> (c0, c1..c7 bases); fg/bg pulled from token table
  "EL-Openglo":    ("10,18,20","255,110,99","85,240,160","255,180,84","79,168,232","176,140,232","0,224,194","140,232,218"),
  "EL-Azure":      ("9,16,24","255,110,99","85,240,160","255,180,84","79,168,255","176,140,232","79,227,232","138,196,242"),
  "EL-Amber":      ("20,16,9","255,110,99","85,240,160","255,235,110","100,170,235","176,140,232","111,216,232","232,196,140"),
  "EL-Openglo-Lit":("11,31,28","166,35,24","10,122,66","138,90,10","10,90,154","106,58,154","0,112,95","96,160,150"),
  "EL-Azure-Lit":  ("8,18,30","166,35,24","10,122,66","138,90,10","20,90,170","106,58,154","6,120,138","90,140,170"),
  "EL-Amber-Lit":  ("33,23,6","150,30,20","6,95,48","108,86,6","20,80,150","100,55,145","8,105,120","150,120,80"),
}

def emit_konsole(t):
    lit = t["tt_is_sel"]
    bg, fg = t["view"], t["fg"]
    cols = ANSI[t["id"]]
    out = [f"[Background]\nColor={bg}\n", f"[BackgroundFaint]\nColor={bg}\n",
           f"[BackgroundIntense]\nColor={t['view_alt']}\n"]
    for i, base in enumerate(cols):
        if i == 0:
            faint = s3(mix(base, bg, 0.35)); intense = t["fg_act"] if lit else s3(mix(base, "255,255,255", 0.12))
        else:
            faint = s3(mix(base, bg, 0.45 if lit else 0.48))
            intense = s3(mix(base, "255,255,255", 0.18 if lit else 0.35))
        out.append(f"[Color{i}]\nColor={base}\n")
        out.append(f"[Color{i}Faint]\nColor={faint}\n")
        out.append(f"[Color{i}Intense]\nColor={intense}\n")
    out += [f"[Foreground]\nColor={fg}\n",
            f"[ForegroundFaint]\nColor={s3(mix(fg, bg, 0.35))}\n",
            f"[ForegroundIntense]\nColor={t['fg_act']}\n",
            "[General]\nAnchors=0.5,0.5\nBlur=false\nColorRandomization=false\n"
            f"Description={t['name']}\nFillStyle=Tile\nOpacity=1\nWallpaper=\n"
            "WallpaperFlipType=NoFlip\nWallpaperOpacity=1\n"]
    return "\n".join(out)

# ------------------------------------------------------------------ audit
def lum(c):
    def f(v):
        v /= 255
        return v/12.92 if v <= 0.03928 else ((v+0.055)/1.055)**2.4
    r, g, b = c
    return 0.2126*f(r)+0.7152*f(g)+0.0722*f(b)

def ratio(a, b):
    la, lb = sorted((lum(rgb(a)), lum(rgb(b))), reverse=True)
    return (la+0.05)/(lb+0.05)

def audit(t):
    rows = [("body/view", t["fg"], t["view"]), ("body/button", t["fg"], t["button"]),
            ("link/view", t["link"], t["view"]), ("neg/view", t["neg"], t["view"]),
            ("neu/view", t["neu"], t["view"]), ("pos/view", t["pos"], t["view"]),
            ("sel", t["sel_fg"], t["sel_bg"])]
    bad = []
    for name, f, b in rows:
        r = ratio(f, b)
        flag = "" if r >= 4.5 else (" *" if r >= 3 else " FAIL")
        if r < 4.5: bad.append((name, round(r, 2)))
        print(f"  {t['id']:16s} {name:12s} {r:5.2f}:1{flag}")
    return bad

# -------------------------------------------------------------------- main
if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(_selftest())
    if "--warm" in sys.argv:
        # ⚑ THE CACHE IS WARMED AS A NAMED STEP, NOT AS A SIDE EFFECT OF WHOEVER
        # IMPORTS FIRST.  Importing this module solves the palette (~108 s cold)
        # and every palette check imports it; run in parallel under paperkit's
        # per-check budget, a cold cache made ~13 checks time out at once and
        # the pre-commit hook refused a green tree — three times on 2026-09-20,
        # each passing on the warm retry. The hook now runs THIS first. The
        # solve happened at import; there is nothing left to do but say so.
        print(f"make_schemes: palette cache warm ({len(GRID)} variants, "
              f"ghost alpha {GHOST_ALPHA})")
        sys.exit(0)
    verify = "--verify" in sys.argv
    for (ph, mode), (t, dark) in GRID.items():
        open(f"{t['id']}.colors", "w").write(emit_colors(t, dark))
        open(f"{t['id']}.colorscheme", "w").write(emit_konsole(t))
        print("wrote", t["id"])
    if verify:
        print("\n-- byte-exact check vs hand-made .colors --")
        import subprocess
        for f in ["EL-Openglo.colors", "EL-Azure.colors", "EL-Openglo-Lit.colors"]:
            r = subprocess.run(["git", "diff", "--no-index", "--stat", f"/tmp/hand/{f}", f],
                               capture_output=True, text=True)
            print(f, "IDENTICAL" if r.returncode == 0 else "DIFFERS")
        print("\n-- WCAG audit --")
        for (ph, mode), (t, d) in GRID.items():
            audit(t)
