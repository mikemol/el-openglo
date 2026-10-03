#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""qt_sandbox.py — the ONE way this tree spawns a Qt tool: headless, sessionless, dumpless.

⚑ W73, MEASURED 2026-09-22 20:28 EDT.  check_ebuild's staging ran make_deb's
⊕RENDER-GATE, which ran render_qml's harness as `qml --apptype widget` with
QT_QPA_PLATFORM=offscreen and the RHI on OpenGL. "offscreen" is not "sessionless":
Qt's offscreen platform opens its GL contexts through GLX on $DISPLAY, so the
harness reached the operator's X server and the NVIDIA driver, SIGSEGV'd inside
libnvidia-glcore under QRhi::endFrame, left a 6.5M core through systemd-coredump,
and raised a KDE crash notification on the desktop. A test must never reach the
desktop session or the GPU driver.

    import qt_sandbox as QT
    r = QT.run([QT.QML, doc], env=base_env, capture_output=True, text=True)
    r = QT.run([QT.QML, ...], mesa=True, ...)  # where pixels need the RHI (bloom)

What `run` does to the child, and why each one:
  - QT_QPA_PLATFORM=offscreen            no window on any display
  - QT_QUICK_BACKEND=software            no RHI, so no GL/Vulkan driver in-process
  - DISPLAY / WAYLAND_DISPLAY / WAYLAND_SOCKET / XAUTHORITY stripped
                                          the offscreen platform cannot FIND the
                                          session, so it cannot open GLX on it
  - KDE_DEBUG=1                          KCrash installs no handler (libKF6Crash
                                          reads it), so no DrKonqi from in-process
  - RLIMIT_CORE soft=hard=0 (launcher)   OPERATOR RULING 2026-09-22: 0. The agent
                                          that wrote this proposed 1, reading
                                          fs/coredump.c and core(5): core_pattern
                                          here pipes to systemd-coredump, and with
                                          a limit of 0 the kernel may still run the
                                          pipe so coredumpd journals the crash
                                          (which DrKonqi's coredump launcher
                                          watches), while exactly 1 aborts before
                                          the helper. That residue is kept, NOT
                                          MEASURED: if a sandboxed crash still
                                          raises DrKonqi, this line is where to look.
                                          `--selftest` measures only that the child
                                          RUNS under the limit.

⚑ THERE IS NO GPU PATH (W158, 2026-10-01).  A gpu=True mode once kept the RHI and
DISPLAY for renders that need MultiEffect's bloom (which draws NOTHING on the
software scene graph), honoured under EL_QT_GPU=1. It reached the GPU driver, the
W73 crash vector. mesa=True replaced it: the same RHI picture on llvmpipe with no GPU
driver. So gpu= is now an unknown keyword (TypeError), EL_QT_GPU means nothing, and
policy/qt_sandbox.rego Q2 denies any call that still asks for the GPU.

⚑ mesa=True IS THE GPU PICTURE WITHOUT THE GPU (W98/W107/W109, measured 2026-09-28).
The child runs as the session client of a PRIVATE `kwin_wayland --virtual` on its own
socket, on QT_QPA_PLATFORM=wayland with EGL pinned to Mesa's vendor file and
LIBGL_ALWAYS_SOFTWARE=1: the RHI draws on llvmpipe (qt.rhi.general: "RENDERER:
llvmpipe"), MultiEffect's bloom renders, and neither DISPLAY nor XAUTHORITY nor any
libnvidia reaches the process (its /proc maps, measured). kwin runs DETACHED and is
SIGKILLed when the child is done (kwin_session): the child's own returncode is run()'s.
⚑ W114, MEASURED 2026-09-28 14:09 EDT: the first version ran the child under kwin
--exit-with-session; kwin crashed (no XDG_RUNTIME_DIR), and DrKonqi plus a "Service
Crash" notification reached the operator's desktop DESPITE KDE_DEBUG=1 and
RLIMIT_CORE=0 (the residue above, now observed for kwin). So kwin is never allowed
an exit of its own: SIGKILL runs no handler and writes no core (0 coredump entries,
measured). Deliberate-crash measurements go to the k8s+kvm VM (operator ruling).
WEAKNESSES: kwin's own EGL init fails and it falls back (harmless); llvmpipe is not
bit-identical to a hardware driver; popen() does not offer it (kwin's lifetime would
have to be the caller's).

WEAKNESS: routing is a property of the CALL; a child that itself spawns a Qt tool
(plasmawindowed launching something) inherits the env but not a re-check. And the
env strip does not stop a child that dials the session bus by a hard-coded path.
"""

import contextlib
import itertools
import os
import shutil
import subprocess
import sys
import time

QT_BIN = "/usr/lib64/qt6/bin"
QML = os.path.join(QT_BIN, "qml")
QMLLINT = os.path.join(QT_BIN, "qmllint")

SESSION_VARS = ("DISPLAY", "WAYLAND_DISPLAY", "WAYLAND_SOCKET", "XAUTHORITY")
CORE_LIMIT = 0  # operator ruling; the 1-vs-0 residue is in the docstring
MESA_EGL = "/usr/share/glvnd/egl_vendor.d/50_mesa.json"
KWIN = "kwin_wayland"
KWIN_ARGS = ("--virtual", "--no-lockscreen", "--no-global-shortcuts")


def env(base=None):
    """The child's environment: `base` (default os.environ) made headless and sessionless,
    on the software scene graph. ⚑ W158: there is no GPU variant any more; a render
    that needs the RHI (bloom) uses mesa=True, which reaches no GPU driver."""
    e = dict(os.environ if base is None else base)
    e["QT_QPA_PLATFORM"] = "offscreen"
    e["KDE_DEBUG"] = "1"
    e["QT_QUICK_BACKEND"] = "software"
    e.pop("QSG_RHI_BACKEND", None)
    for k in SESSION_VARS:
        e.pop(k, None)
    return e


def mesa_env(base=None):
    """The kwin + client environment for mesa=True: sessionless, RHI on OpenGL, Mesa EGL."""
    e = dict(os.environ if base is None else base)
    for k in SESSION_VARS + ("QT_QPA_PLATFORM",):
        e.pop(k, None)
    e.update(
        KDE_DEBUG="1",
        QT_QUICK_BACKEND="rhi",
        QSG_RHI_BACKEND="opengl",
        __EGL_VENDOR_LIBRARY_FILENAMES=MESA_EGL,
        LIBGL_ALWAYS_SOFTWARE="1",
    )
    # kwin binds its socket under XDG_RUNTIME_DIR; a base without it (the selftest's
    # minimal one) made kwin SIGSEGV (rc -11, measured 2026-09-28)
    if "XDG_RUNTIME_DIR" not in e and os.environ.get("XDG_RUNTIME_DIR"):
        e["XDG_RUNTIME_DIR"] = os.environ["XDG_RUNTIME_DIR"]
    return e


def backend_facts(mesa=False):
    """What this module does to a render's PIXELS, as data (W159): the variables the
    route sets or removes, and kwin's argv on the Mesa route. A cache key holds this
    in place of the file's bytes, so a comment, the core limit or a selftest edit stops
    invalidating screenshots. DERIVED by running env()/mesa_env() over an empty
    base, never listed by hand, so a new override shows up here by construction.
    WEAKNESS: kwin's binary and Mesa's llvmpipe are host facts, keyed by the host
    fingerprint, not here; a code path that changes pixels outside these
    functions (none today) would escape it."""
    probe = {k: "@" for k in SESSION_VARS + ("QT_QPA_PLATFORM", "QSG_RHI_BACKEND")}
    e = (mesa_env if mesa else env)(dict(probe))
    e.pop("XDG_RUNTIME_DIR", None)
    return {
        "route": "mesa" if mesa else "software",
        "set": {k: v for k, v in sorted(e.items()) if probe.get(k) != v},
        "removed": sorted(k for k in probe if k not in e),
        "kwin": [KWIN, *KWIN_ARGS] if mesa else None,
    }


@contextlib.contextmanager
def kwin_session(e, ready_s=30):
    """A private `kwin_wayland --virtual` for the duration of the block; yields its
    socket name. ⚑ W114: kwin is NEVER left to exit on its own: the block's end
    SIGKILLs it, and SIGKILL runs no crash handler and writes no core, so nothing can
    reach DrKonqi or the desktop (measured 2026-09-28: 0 coredump entries). The old
    --exit-with-session route let a kwin teardown/startup crash page the operator."""
    sock = f"el-qt-{os.getpid()}-{next(_SOCKETS)}"
    path = os.path.join(e.get("XDG_RUNTIME_DIR", ""), sock)
    k = subprocess.Popen(
        launch_argv([KWIN, *KWIN_ARGS, "--socket", sock]),
        env=e,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        t0 = time.monotonic()
        while not os.path.exists(path):
            if k.poll() is not None:
                raise RuntimeError(
                    f"qt_sandbox: {KWIN} exited rc={k.returncode} before its socket appeared"
                )
            if time.monotonic() - t0 > ready_s:
                raise RuntimeError(
                    f"qt_sandbox: {KWIN} socket {sock} not ready in {ready_s}s"
                )
            time.sleep(0.05)
        yield sock
    finally:
        k.kill()
        k.wait()


_SOCKETS = itertools.count()


# ⚑ THE LIMITS ARE SET BY A LAUNCHER, NOT BY preexec_fn (2026-10-03, ruff PLW1509: preexec_fn
# runs Python between fork and exec and is unsafe in a threaded parent - the documented
# deadlock; the repo is held to ruff's default bar by mtools' pycheck hook). The launcher is
# the child's own first act: it sets RLIMIT_CORE (and RLIMIT_CPU when asked) and then
# EXECS the real command, so the pid, the environment and the inherited limits are exactly
# what the preexec route gave; the selftest measures the limit in a real child. argv[1] is
# the core limit, argv[2] the cpu cap in seconds or -1, argv[3:] the command.
_LAUNCHER = (
    "import os, resource, sys\n"
    "core, cpu = int(sys.argv[1]), int(sys.argv[2])\n"
    "resource.setrlimit(resource.RLIMIT_CORE, (core, core))\n"
    "if cpu >= 0:\n"
    "    resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu))\n"
    "os.execvp(sys.argv[3], sys.argv[3:])\n"
)


def launch_argv(cmd, cpu=None):
    """`cmd` wrapped so the child leaves no core (and wakes no coredump helper), and is CPU-capped
    when `cpu` is given: the launcher sets the limits, then execs `cmd`."""
    if isinstance(cmd, (str, bytes)):
        raise TypeError("qt_sandbox: the command is an argv list, never a shell string")
    return [
        sys.executable,
        "-c",
        _LAUNCHER,
        str(CORE_LIMIT),
        str(-1 if cpu is None else int(cpu)),
        *map(os.fspath, cmd),
    ]


def run(cmd, env=None, cpu=None, mesa=False, **kw):
    """subprocess.run under env(env) (or the mesa route) and no_core. The one Qt spawn in the tree.
    `cpu` (seconds) caps the child's OWN CPU (RLIMIT_CPU) — the budget that means the
    same on an idle host and a loaded one. A wall `timeout` alone failed healthy
    harnesses while the pre-commit gate loaded the box (2026-09-25,
    check_marquee_body: 60 s wall, PASS alone); keep a wall timeout only as a
    generous hang guard (a stalled harness burns no CPU)."""
    if "preexec_fn" in kw:
        raise TypeError("qt_sandbox.run owns preexec_fn")
    argv = launch_argv(cmd, cpu)
    if mesa:
        e = mesa_env(env)
        with kwin_session(e) as sock:
            return subprocess.run(
                argv,
                env=dict(e, WAYLAND_DISPLAY=sock, QT_QPA_PLATFORM="wayland"),
                check=kw.pop("check", False),
                **kw,
            )
    return subprocess.run(
        argv, env=globals()["env"](env), check=kw.pop("check", False), **kw
    )


def popen(cmd, env=None, mesa=False, **kw):
    """subprocess.Popen under the same env and core limit (launch_argv) as run(): for a harness whose
    measurement must be STREAMED (check_marquee_live ends at its RESULT line and
    kills a teardown hang, W63), which run() cannot do."""
    if mesa:
        raise TypeError(
            "qt_sandbox.popen: mesa=True not offered yet (the wrapper dir must outlive the call)"
        )
    if "preexec_fn" in kw:
        raise TypeError("qt_sandbox.popen owns preexec_fn")
    return subprocess.Popen(launch_argv(cmd), env=globals()["env"](env), **kw)


def _selftest():
    ok = True

    def check(label, got, want):
        nonlocal ok
        print(
            ("  ok   " if got == want else "  FAIL ")
            + f"{label}"
            + ("" if got == want else f": got {got!r} want {want!r}")
        )
        ok = ok and got == want

    base = {
        "DISPLAY": ":0",
        "WAYLAND_DISPLAY": "wayland-0",
        "XAUTHORITY": "/x",
        "QT_QUICK_BACKEND": "rhi",
        "QSG_RHI_BACKEND": "opengl",
        "PATH": "/bin",
    }
    e = env(base)
    check("the session is stripped", [k for k in SESSION_VARS if k in e], [])
    check("offscreen platform", e["QT_QPA_PLATFORM"], "offscreen")
    check(
        "a caller's rhi request is overridden to software",
        e["QT_QUICK_BACKEND"],
        "software",
    )
    check("KCrash off", e["KDE_DEBUG"], "1")
    check("the base is not mutated", base["DISPLAY"], ":0")
    # ⚑ W158: the GPU path is GONE, not merely off: asking for it is a TypeError,
    # and EL_QT_GPU in the environment changes nothing.
    for spawn in (run, popen):
        try:
            spawn(["true"], gpu=True)
            check(f"{spawn.__name__}(gpu=True) is refused", False, True)
        except TypeError:
            check(f"{spawn.__name__}(gpu=True) is refused", True, True)
    saved = os.environ.get("EL_QT_GPU")
    os.environ["EL_QT_GPU"] = "1"
    try:
        check(
            "EL_QT_GPU=1 no longer changes the backend",
            env(base)["QT_QUICK_BACKEND"],
            "software",
        )
    finally:
        if saved is None:
            os.environ.pop("EL_QT_GPU")
        else:
            os.environ["EL_QT_GPU"] = saved
    # ⚑ THE CHILD MUST SEE THE LIMIT AND THE STRIPPED ENV — measured in a real child.
    r = run(
        [
            sys.executable,
            "-c",
            (
                "import os,resource;print(resource.getrlimit(resource.RLIMIT_CORE),"
                "os.environ.get('DISPLAY'),os.environ['QT_QPA_PLATFORM'])"
            ),
        ],
        env=base,
        capture_output=True,
        text=True,
    )
    # The literal 0 is the operator's ruling, not CORE_LIMIT: an edit back to 1
    # must turn this red, not silently agree with itself.
    check(
        "a child runs with RLIMIT_CORE=0, no DISPLAY, offscreen",
        r.stdout.strip(),
        "(0, 0) None offscreen",
    )
    p = popen(
        [
            sys.executable,
            "-c",
            (
                "import os,resource;print(resource.getrlimit(resource.RLIMIT_CORE),"
                "os.environ.get('DISPLAY'),os.environ['QT_QPA_PLATFORM'])"
            ),
        ],
        env=base,
        stdout=subprocess.PIPE,
        text=True,
    )
    out, _ = p.communicate()
    check(
        "popen's child is sandboxed the same way", out.strip(), "(0, 0) None offscreen"
    )
    # the CPU cap (run's `cpu`) is set by the same launcher: measured in a real child, and
    # absent when not asked (RLIM_INFINITY is -1)
    for cap, want in ((7, "(7, 7)"), (None, "(-1, -1)")):
        r = run(
            [
                sys.executable,
                "-c",
                "import resource;print(resource.getrlimit(resource.RLIMIT_CPU))",
            ],
            env=base,
            cpu=cap,
            capture_output=True,
            text=True,
        )
        check(
            f"run(cpu={cap}) gives the child RLIMIT_CPU {want}", r.stdout.strip(), want
        )
    try:
        run(["true"], preexec_fn=lambda: None)
        check("a caller's preexec_fn is refused", False, True)
    except TypeError:
        check("a caller's preexec_fn is refused", True, True)
    # ⚑ THE MESA ROUTE (W108): env and wrapper by construction, then a REAL child.
    m = mesa_env(base)
    check(
        "mesa: the session and platform are stripped",
        [k for k in SESSION_VARS + ("QT_QPA_PLATFORM",) if k in m],
        [],
    )
    check(
        "mesa: rhi on opengl over Mesa EGL, software GL",
        (
            m["QT_QUICK_BACKEND"],
            m["QSG_RHI_BACKEND"],
            m["__EGL_VENDOR_LIBRARY_FILENAMES"],
            m["LIBGL_ALWAYS_SOFTWARE"],
        ),
        ("rhi", "opengl", MESA_EGL, "1"),
    )
    if not shutil.which(KWIN):
        print(f"  SKIP mesa child arms — {KWIN} is not installed")
    else:
        r = run(
            [
                sys.executable,
                "-c",
                (
                    "import os,resource;print(resource.getrlimit(resource.RLIMIT_CORE),"
                    "os.environ.get('DISPLAY'),os.environ['QT_QPA_PLATFORM'],"
                    "os.environ['LIBGL_ALWAYS_SOFTWARE'])"
                ),
            ],
            env=base,
            mesa=True,
            capture_output=True,
            text=True,
            timeout=120,
        )
        check(
            "mesa: a real child runs core-less, no DISPLAY, on wayland, software GL",
            r.stdout.strip().splitlines()[-1:],
            ["(0, 0) None wayland 1"],
        )
        r = run(
            ["sh", "-c", "exit 3"],
            env=base,
            mesa=True,
            capture_output=True,
            text=True,
            timeout=120,
        )
        check("mesa: run() returns the child's own code", r.returncode, 3)

        # ⚑ W114: kwin must leave NO crash record. Counted before/after the two runs above
        # would race coredumpd, so count around one more run with a settle.
        def kwin_dumps():
            c = subprocess.run(
                ["coredumpctl", "list", KWIN, "--no-pager", "-q"],
                capture_output=True,
                text=True,
                check=False,
            )
            return c.stdout.count("\n") if c.returncode in (0, 1) else None

        before = kwin_dumps()
        run(["true"], env=base, mesa=True, timeout=120)
        time.sleep(2)
        after = kwin_dumps()
        if before is None or after is None:
            print("  SKIP mesa no-crash-record arm — coredumpctl unreadable here")
        else:
            check(
                "mesa: kwin leaves no coredump record (SIGKILLed, never crashes)",
                after - before,
                0,
            )
        # and a kwin not ready in time is REFUSED, not reported as the child's result.
        # ⚑ ready_s=0, NEVER a broken env: a kwin without XDG_RUNTIME_DIR SIGSEGVs and
        # pages the operator (the 14:09 incident); a timeout only SIGKILLs it.
        try:
            with kwin_session(mesa_env(base), ready_s=0):
                pass
            check(
                "mesa: a kwin whose socket is not ready in time is refused", False, True
            )
        except RuntimeError:
            check(
                "mesa: a kwin whose socket is not ready in time is refused", True, True
            )
    print("qt_sandbox selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    args = sys.argv[1:]
    for a in args:
        if a != "--selftest":
            print(f"qt_sandbox: unknown flag {a!r}", file=sys.stderr)
            sys.exit(2)
    if "--selftest" not in args:
        print("qt_sandbox: a library; run --selftest", file=sys.stderr)
        sys.exit(2)
    sys.exit(0 if _selftest() else 1)
