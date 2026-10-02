# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""screens_viewport — the pinholes-anim APNG: post-render code for ONE output kind (W61).

Split out of render_screens.py so that this assembly code keys only the outputs it
shapes (pinholes-anim-*), not every screen: keyed whole in render_screens, a comment
anywhere in that file moved 55 of 56 output keys (measured 2026-10-02).
"""
import os
import sys

FRAME_MS = 40


def animate_viewport(variant, out_apng, job, want):
    """The text probe rendered once per band of its backdrop, assembled as an APNG:
    the field scrolling down a 16-row Unifont cell and back. Returns the frame count.

    ⚑ ONE qml PROCESS FOR ALL FRAMES (render speed #2): render_qml.render_frames
    steps the probe's plasmoid.configuration BINDING and grabs each step. The field's
    read-back per frame must equal step x scale (`want`) — a frame whose binding did
    not deliver its step is refused, not assembled. A frame count short of the plan
    is also refused (0): the old loop silently dropped a failed step (64 of 65 once,
    measured) and the ping-pong was then no longer symmetric."""
    import tempfile
    import render_qml as RQ
    from PIL import Image
    s, w, h, key, steps, probe = job
    with tempfile.TemporaryDirectory() as td:
        # the same backend as the stills (rhi where the host has it): the frames
        # must look like the picture beside them
        rc, err, seen = RQ.render_frames(s, variant, w, h, td, key, steps, probe)
        names = sorted(n for n in os.listdir(td) if n.startswith("frame-"))
        if rc != 0 or seen != want or len(names) != len(steps):
            print(f"render_screens: pinholes-anim {variant} REFUSED — rc={rc}, {len(names)} of "
                  f"{len(steps)} frames, read back {seen!r}\n{err[-400:]}", file=sys.stderr)
            return 0
        ims = [Image.open(os.path.join(td, n)).convert("RGB") for n in names]
    ims[0].save(out_apng, format="PNG", save_all=True, append_images=ims[1:], duration=FRAME_MS, loop=0)
    return len(ims)
