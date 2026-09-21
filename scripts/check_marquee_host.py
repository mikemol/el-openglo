#!/usr/bin/env python3
"""check_marquee_host.py — what the marquee did on THIS desktop, read from the appletsrc.

⚑ WHY (operator, 2026-09-22: "check the logs yourself on ticks; I won't promise
to be timely, and you'll do a better job searching the logs anyway"). The
running plasmashell was started from a terminal (`plasmashell --replace &`), so
its stderr is /dev/pts/N — readable by nobody else. The widget therefore keeps
the tail of its own trace in `plasmoid.configuration.traceLog`, which Plasma
persists to ~/.config/plasma-org.kde.plasma.desktop-appletsrc. This reads every
marquee applet group there: is the log switched on, which build's settings it
carries, and the trace lines themselves — the live host's twin of
check_marquee_live --trace.

    scripts/check_marquee_host.py            # every marquee instance: settings + trace
    scripts/check_marquee_host.py --json     # the same, as the measurement
    scripts/check_marquee_host.py --selftest

WEAKNESS: KConfig writes are debounced and the shell may hold changes until it
syncs; a line printed a second ago may not be on disk yet. And a widget whose
debugLog is OFF writes nothing — reported as such, never as "no events".
"""
import configparser
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APPLETSRC = os.path.expanduser("~/.config/plasma-org.kde.plasma.desktop-appletsrc")
PLUGIN_PREFIX = "org.el.notifymarquee"    # the one package (W35) and the older per-variant ids


def instances(path=APPLETSRC):
    """[{group, plugin, debugLog, hoverPause, trace: [lines]}] for every marquee applet."""
    if not os.path.isfile(path):
        return None
    cp = configparser.ConfigParser(interpolation=None, strict=False, delimiters=("=",))
    cp.optionxform = str
    cp.read(path, encoding="utf-8")
    out = []
    for section in cp.sections():
        plugin = cp[section].get("plugin", "")
        if not plugin.startswith(PLUGIN_PREFIX):
            continue
        general = f"{section}][Configuration][General"
        conf = cp[general] if cp.has_section(general) else {}
        raw = conf.get("traceLog", "") if conf else ""
        # KConfig escapes newlines in a String entry as \n
        lines = [l for l in raw.replace("\\n", "\n").split("\n") if l.strip()]
        out.append({
            "group": section, "plugin": plugin,
            "debugLog": (conf.get("debugLog", "false") if conf else "false") == "true",
            "hoverPause": (conf.get("hoverPause", "true") if conf else "true") == "true",
            "trace": lines,
        })
    return out


def journal(since="-2h"):
    """el-marquee lines from the user journal — present only when plasmashell runs
    under its systemd unit (or systemd-cat); this qtbase has no journald USE, so
    Qt itself never writes there. None when journalctl is absent."""
    import shutil
    import subprocess
    if not shutil.which("journalctl"):
        return None
    r = subprocess.run(["journalctl", "--user", "--no-pager", "-o", "cat", "--since", since, "-g", "el-marquee"],
                       capture_output=True, text=True, timeout=60)
    return [l.split("el-marquee ", 1)[1] for l in r.stdout.splitlines() if "el-marquee " in l]


def shell_stderr():
    """Where the running plasmashell's stderr goes (a tty means: unreadable here)."""
    import subprocess
    r = subprocess.run(["pgrep", "-x", "plasmashell"], capture_output=True, text=True)
    pids = r.stdout.split()
    if not pids:
        return "plasmashell is not running"
    try:
        return os.readlink(f"/proc/{pids[0]}/fd/2")
    except OSError as e:
        return f"unreadable ({e})"


def main(argv):
    known = {"--json", "--selftest"}
    for a in argv[1:]:
        if a not in known:
            print(f"check_marquee_host: unknown flag {a!r}", file=sys.stderr)
            return 2
    rows = instances()
    if rows is None:
        print(f"check_marquee_host: SKIP — {APPLETSRC} is not on this host", file=sys.stderr)
        return 0
    jl = journal()
    err = shell_stderr()
    if "--json" in argv:
        print(json.dumps({"appletsrc": APPLETSRC, "instances": rows, "shell_stderr": err,
                          "journal": jl if jl is not None else []}, indent=1))
        return 0
    print(f"plasmashell stderr -> {err}" + ("  (a tty: only the appletsrc trace is readable here)" if "/pts/" in err else ""))
    print(f"journal: {len(jl) if jl is not None else 'no journalctl'} el-marquee line(s) in the last 2h")
    for l in (jl or [])[-40:]:
        print(f"    {l}")
    if not rows:
        print(f"check_marquee_host: 0 marquee applets in {APPLETSRC}")
        return 0
    for r in rows:
        print(f"{r['plugin']} [{r['group']}]  debugLog={'on' if r['debugLog'] else 'OFF'}  "
              f"hoverPause={'on' if r['hoverPause'] else 'off'}  {len(r['trace'])} trace line(s)")
        for l in r["trace"]:
            print(f"    {l}")
    return 0


def _selftest():
    ok = True

    def chk(label, got, want):
        nonlocal ok
        print(f"  {'ok  ' if got == want else 'FAIL'} {label}" + ("" if got == want else f": got {got!r} want {want!r}"))
        ok = ok and got == want

    import tempfile
    fixture = ("[Containments][1][Applets][7]\nplugin=org.el.notifymarquee.elopenglo\n\n"
               "[Containments][1][Applets][7][Configuration][General]\ndebugLog=true\n"
               "traceLog=0.10 upsert id=3 text=\"app: hi\"\\n0.11 swap live=[3] ring=[3]\\n\n"
               "[Containments][1][Applets][8]\nplugin=org.kde.plasma.digitalclock\n")
    with tempfile.NamedTemporaryFile("w", suffix=".rc", delete=False) as f:
        f.write(fixture)
        p = f.name
    rows = instances(p)
    os.unlink(p)
    chk("only marquee applets are read", [r["plugin"] for r in rows], ["org.el.notifymarquee.elopenglo"])
    chk("the log switch is read", rows[0]["debugLog"], True)
    chk("escaped newlines split the trace", rows[0]["trace"], ['0.10 upsert id=3 text="app: hi"', "0.11 swap live=[3] ring=[3]"])
    chk("an absent appletsrc is None, not empty", instances("/nonexistent/appletsrc"), None)
    print("check_marquee_host selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
