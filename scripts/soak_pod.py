#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""soak_pod.py — run a staged marquee soak (marquee_soak.py stage) in a memory-limited k8s Pod.

⚑ WHY (operator, 2026-10-12: the widget exhausted the desktop's RAM and swap; luthen-observability:
W838). The repro runs where a runaway cannot reach the desktop: the throwaway-el-openglo
namespace, a Pod with a hard memory limit and a TTL, on luthen's runnable qt-stage image
(luthen-observability:W841). The staged directory travels as a ConfigMap (a tar.gz in
binaryData, plus marquee_soak.py itself, which the Pod runs stdlib-only).

    scripts/soak_pod.py DIR --image REF [--seconds N] [--memory 2Gi] [--name NAME]
                                    # submit, wait, print the Pod's log (samples + summary), delete
    scripts/soak_pod.py DIR --image REF --dry-run    # server-side admission check only
    scripts/soak_pod.py --selftest

Exit 0 when the soak ran to a summary, 1 when the Pod failed or printed none.

WEAKNESS: it measures what the OFFSCREEN software scene graph does (see marquee_soak.py); a
clean result clears the QML, not the widget's Wayland buffers. Admission rules beyond the
documented ones (TTL annotation, activeDeadlineSeconds <= 1800) are learnt from the server's
refusal, which this prints verbatim. The Pod and ConfigMap are deleted on every exit path
except --dry-run (which creates nothing).
"""

import base64
import io
import json
import os
import subprocess
import sys
import tarfile
import time

NAMESPACE = "throwaway-el-openglo"
FLAGS = {"--image", "--seconds", "--memory", "--name", "--dry-run", "--selftest"}
HERE = os.path.dirname(os.path.abspath(__file__))


def pack(directory):
    """The staged directory as a base64 tar.gz."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        tar.add(directory, arcname=".")
    return base64.b64encode(buf.getvalue()).decode()


def manifests(directory, image, name, seconds, memory):
    """[ConfigMap, Pod] for one soak: the shape the namespace's admission asks for."""
    with open(os.path.join(HERE, "marquee_soak.py")) as fh:
        script = fh.read()
    command = (
        "mkdir /soak && tar xzf /cfg/soak.tgz -C /soak "
        f"&& python3 /cfg/marquee_soak.py run /soak --seconds {int(seconds)} --every 2 "
        "; echo ---SAMPLES---; cat /soak/samples.jsonl; echo ---SUMMARY---; cat /soak/summary.json"
    )
    meta = {"name": name, "namespace": NAMESPACE}
    config = {
        "apiVersion": "v1",
        "kind": "ConfigMap",
        "metadata": dict(meta),
        "data": {"marquee_soak.py": script},
        "binaryData": {"soak.tgz": pack(directory)},
    }
    pod = {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {
            **meta,
            "annotations": {"luthen.io/ttl-seconds": "1800"},
        },
        "spec": {
            "restartPolicy": "Never",
            "activeDeadlineSeconds": min(1800, int(seconds) + 300),
            "containers": [
                {
                    "name": "soak",
                    "image": image,
                    "imagePullPolicy": "Never",
                    "command": ["sh", "-c", command],
                    "env": [{"name": "HOME", "value": "/tmp"}],
                    "resources": {
                        "limits": {"memory": memory, "cpu": "1"},
                        "requests": {"memory": memory, "cpu": "1"},
                    },
                    "volumeMounts": [{"name": "cfg", "mountPath": "/cfg"}],
                }
            ],
            "volumes": [{"name": "cfg", "configMap": {"name": name}}],
        },
    }
    return [config, pod]


def kubectl(*args, stdin=None):
    return subprocess.run(
        ["kubectl", "-n", NAMESPACE, *args],
        input=stdin,
        capture_output=True,
        text=True,
        check=False,
    )


def submit(directory, image, seconds, memory, name, dry_run):
    docs = manifests(directory, image, name, seconds, memory)
    stdin = json.dumps({"apiVersion": "v1", "kind": "List", "items": docs})
    flag = ["--dry-run=server"] if dry_run else []
    r = kubectl("apply", "-f", "-", *flag, stdin=stdin)
    print(r.stdout + r.stderr, end="")
    if r.returncode != 0 or dry_run:
        return r.returncode
    try:
        phase = ""
        end = time.monotonic() + seconds + 330
        while time.monotonic() < end:
            phase = kubectl(
                "get", "pod", name, "-o", "jsonpath={.status.phase}"
            ).stdout.strip()
            if phase in ("Succeeded", "Failed"):
                break
            time.sleep(5)
        log = kubectl("logs", name).stdout
        print(log)
        return 0 if phase == "Succeeded" and "---SUMMARY---" in log else 1
    finally:
        kubectl("delete", "pod,configmap", name, "--ignore-not-found")


def _selftest():
    import tempfile

    ok = True

    def chk(label: str, got: object, want: object) -> None:
        nonlocal ok
        print(
            f"  {'ok  ' if got == want else 'FAIL'} {label}"
            + ("" if got == want else f": got {got!r} want {want!r}")
        )
        ok = ok and got == want

    with tempfile.TemporaryDirectory() as td:
        with open(os.path.join(td, "soak.json"), "w") as fh:
            fh.write("{}")
        cm, pod = manifests(td, "img:x", "soak-t", 90, "2Gi")
        spec = pod["spec"]
        c = spec["containers"][0]
        chk(
            "the TTL annotation is set",
            pod["metadata"]["annotations"],
            {"luthen.io/ttl-seconds": "1800"},
        )
        chk(
            "the deadline is the run plus grace and within 1800",
            spec["activeDeadlineSeconds"],
            390,
        )
        chk(
            "a long soak's deadline is capped at 1800",
            manifests(td, "i", "n", 5000, "2Gi")[1]["spec"]["activeDeadlineSeconds"],
            1800,
        )
        chk("the image is local to the node", c["imagePullPolicy"], "Never")
        chk(
            "the memory limit is the one asked for",
            c["resources"]["limits"]["memory"],
            "2Gi",
        )
        chk(
            "the pod and the config map share a namespace",
            pod["metadata"]["namespace"],
            cm["metadata"]["namespace"],
        )
        tar = base64.b64decode(cm["binaryData"]["soak.tgz"])
        with tarfile.open(fileobj=io.BytesIO(tar)) as t:
            names = t.getnames()
        chk("the packed tar carries the staged files", "./soak.json" in names, True)
    print("soak_pod selftest:", "PASS" if ok else "FAIL")
    return ok


def main(argv):
    args = argv[1:]
    for a in args:
        if a.startswith("--") and a not in FLAGS:
            print(f"soak_pod: unknown flag '{a}'", file=sys.stderr)
            return 2
    if "--selftest" in args:
        return 0 if _selftest() else 1
    # 1Gi is the namespace's per-container maximum (admission refused 2Gi, measured 2026-10-12)
    opts = {"--seconds": "120", "--memory": "1Gi", "--name": f"soak-{int(time.time())}"}
    dry = "--dry-run" in args
    if dry:
        args.remove("--dry-run")
    for flag in ("--image", "--seconds", "--memory", "--name"):
        if flag in args:
            i = args.index(flag)
            if i + 1 >= len(args):
                print(f"soak_pod: {flag} needs a value", file=sys.stderr)
                return 2
            opts[flag] = args.pop(i + 1)
            args.pop(i)
    if len(args) != 1 or "--image" not in opts:
        print(
            "usage: soak_pod.py DIR --image REF [--seconds N] [--memory M] [--name N] [--dry-run]",
            file=sys.stderr,
        )
        return 2
    directory = os.path.abspath(args[0])
    if not os.path.isfile(os.path.join(directory, "soak.json")):
        print(
            f"soak_pod: {directory} holds no soak.json: run marquee_soak.py stage first",
            file=sys.stderr,
        )
        return 2
    return submit(
        directory,
        opts["--image"],
        float(opts["--seconds"]),
        opts["--memory"],
        opts["--name"],
        dry,
    )


if __name__ == "__main__":
    sys.exit(main(sys.argv))
