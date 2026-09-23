#!/usr/bin/env python3
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
    r = QT.run([QT.QML, ...], gpu=True, ...)   # ONLY where pixels need the RHI

What `run` does to the child, and why each one:
  - QT_QPA_PLATFORM=offscreen            no window on any display
  - QT_QUICK_BACKEND=software            no RHI, so no GL/Vulkan driver in-process
  - DISPLAY / WAYLAND_DISPLAY / WAYLAND_SOCKET / XAUTHORITY stripped
                                          the offscreen platform cannot FIND the
                                          session, so it cannot open GLX on it
  - KDE_DEBUG=1                          KCrash installs no handler (libKF6Crash
                                          reads it), so no DrKonqi from in-process
  - RLIMIT_CORE soft=hard=0 (preexec)    OPERATOR RULING 2026-09-22: 0. The agent
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

⚑ gpu=True IS THE ONE EXCEPTION, AND IT IS NAMED AT THE CALL SITE.  render_qml's
harness asks for the RHI because MultiEffect (the bloom halo) draws NOTHING on the
software scene graph (measured: bloom=4 and bloom=0 byte-identical). gpu=True keeps
the RHI backend and keeps DISPLAY (offscreen GL needs GLX), so it still reaches the
GPU driver — the crash vector — but never dumps a core or raises DrKonqi. It is
honoured only when EL_QT_GPU=1 is in the caller's environment; otherwise it is
software like everything else, and the caller's own backend report says so.
scripts/check_qt_sandbox.py lists every gpu=True site; the operator decides.

WEAKNESS: routing is a property of the CALL; a child that itself spawns a Qt tool
(plasmawindowed launching something) inherits the env but not a re-check. And the
env strip does not stop a child that dials the session bus by a hard-coded path.
"""
import os
import resource
import subprocess
import sys

QT_BIN = "/usr/lib64/qt6/bin"
QML = os.path.join(QT_BIN, "qml")
QMLLINT = os.path.join(QT_BIN, "qmllint")

SESSION_VARS = ("DISPLAY", "WAYLAND_DISPLAY", "WAYLAND_SOCKET", "XAUTHORITY")
CORE_LIMIT = 0        # operator ruling; the 1-vs-0 residue is in the docstring


def gpu_allowed():
    """True iff the operator opted this process into the GPU scene graph (EL_QT_GPU=1)."""
    return os.environ.get("EL_QT_GPU") == "1"


def env(base=None, gpu=False):
    """The child's environment: `base` (default os.environ) made headless and sessionless."""
    e = dict(os.environ if base is None else base)
    use_gpu = gpu and gpu_allowed()
    e["QT_QPA_PLATFORM"] = "offscreen"
    e["KDE_DEBUG"] = "1"
    if use_gpu:
        e.setdefault("QT_QUICK_BACKEND", "rhi")
        # GLX needs DISPLAY AND its authority: without XAUTHORITY the server refuses
        # ("Authorization required") and Qt aborts creating the context — measured
        # 2026-09-23, every GPU render rc=-6. Nothing else of the session passes.
        for k in ("WAYLAND_DISPLAY", "WAYLAND_SOCKET"):
            e.pop(k, None)
    else:
        e["QT_QUICK_BACKEND"] = "software"
        e.pop("QSG_RHI_BACKEND", None)
        for k in SESSION_VARS:
            e.pop(k, None)
    return e


def no_core():
    """preexec_fn: this child can leave no core and wake no coredump helper."""
    resource.setrlimit(resource.RLIMIT_CORE, (CORE_LIMIT, CORE_LIMIT))


def run(cmd, env=None, gpu=False, **kw):
    """subprocess.run under env(env, gpu) and no_core. The one Qt spawn in the tree."""
    if "preexec_fn" in kw:
        raise TypeError("qt_sandbox.run owns preexec_fn")
    return subprocess.run(cmd, env=globals()["env"](env, gpu), preexec_fn=no_core, **kw)


def popen(cmd, env=None, gpu=False, **kw):
    """subprocess.Popen under the same env and no_core as run(): for a harness whose
    measurement must be STREAMED (check_marquee_live ends at its RESULT line and
    kills a teardown hang, W63), which run() cannot do."""
    if "preexec_fn" in kw:
        raise TypeError("qt_sandbox.popen owns preexec_fn")
    return subprocess.Popen(cmd, env=globals()["env"](env, gpu), preexec_fn=no_core, **kw)


def _selftest():
    ok = True

    def check(label, got, want):
        nonlocal ok
        print(("  ok   " if got == want else "  FAIL ") + f"{label}" +
              ("" if got == want else f": got {got!r} want {want!r}"))
        ok = ok and got == want

    base = {"DISPLAY": ":0", "WAYLAND_DISPLAY": "wayland-0", "XAUTHORITY": "/x",
            "QT_QUICK_BACKEND": "rhi", "QSG_RHI_BACKEND": "opengl", "PATH": "/bin"}
    e = env(base)
    check("the session is stripped", [k for k in SESSION_VARS if k in e], [])
    check("offscreen platform", e["QT_QPA_PLATFORM"], "offscreen")
    check("a caller's rhi request is overridden to software", e["QT_QUICK_BACKEND"], "software")
    check("KCrash off", e["KDE_DEBUG"], "1")
    check("the base is not mutated", base["DISPLAY"], ":0")
    saved = os.environ.pop("EL_QT_GPU", None)
    check("gpu=True without EL_QT_GPU=1 is software", env(base, gpu=True)["QT_QUICK_BACKEND"], "software")
    os.environ["EL_QT_GPU"] = "1"
    g = env(base, gpu=True)
    check("gpu=True with EL_QT_GPU=1 keeps the rhi", g["QT_QUICK_BACKEND"], "rhi")
    check("...and DISPLAY + XAUTHORITY only", [k for k in SESSION_VARS if k in g],
          ["DISPLAY", "XAUTHORITY"])
    if saved is None:
        os.environ.pop("EL_QT_GPU")
    else:
        os.environ["EL_QT_GPU"] = saved
    # ⚑ THE CHILD MUST SEE THE LIMIT AND THE STRIPPED ENV — measured in a real child.
    r = run([sys.executable, "-c",
             "import os,resource;print(resource.getrlimit(resource.RLIMIT_CORE),"
             "os.environ.get('DISPLAY'),os.environ['QT_QPA_PLATFORM'])"],
            env=base, capture_output=True, text=True)
    # The literal 0 is the operator's ruling, not CORE_LIMIT: an edit back to 1
    # must turn this red, not silently agree with itself.
    check("a child runs with RLIMIT_CORE=0, no DISPLAY, offscreen",
          r.stdout.strip(), "(0, 0) None offscreen")
    p = popen([sys.executable, "-c",
               "import os,resource;print(resource.getrlimit(resource.RLIMIT_CORE),"
               "os.environ.get('DISPLAY'),os.environ['QT_QPA_PLATFORM'])"],
              env=base, stdout=subprocess.PIPE, text=True)
    out, _ = p.communicate()
    check("popen's child is sandboxed the same way", out.strip(), "(0, 0) None offscreen")
    try:
        run(["true"], preexec_fn=lambda: None)
        check("a caller's preexec_fn is refused", False, True)
    except TypeError:
        check("a caller's preexec_fn is refused", True, True)
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
