# The guest image (W71): scoping

luthen-observability will run throwaway VMs through k8s. A peer submits a manifest: a
KubeVirt VMI for boot and GUI work, or a plain Pod for userspace work. **That surface is
not built yet.** luthen has said the guest image is ours to build. This document
decides what the image is, so that the image exists when the surface does.

## Limits the surface imposes (operator, relayed by luthen-observability, 2026-09-22)

The source is luthen's design, `~/github/luthen-observability/docs/w45-surface-design.md`,
in §3 and in "Operator rulings". None of it is built on luthen's side yet.

| limit | value | consequence here |
|-------|-------|------------------|
| TTL | **30 min per VM** (1800 s). A request above the max is **refused**, not clamped | every probe has to finish, and its artifacts have to be copied out, well inside 30 min |
| memory | **1 GiB per environment, including KubeVirt's launcher overhead**. A request above the max is **refused**, not clamped | see the memory budget (e) below |
| namespace | one per peer (`throwaway-el-openglo`) | only our own SA can open our VNC and console |
| control channel | **no QMP client access** | screenshots come from `vnc/screenshot`. Keys go over VNC (RFB). Journal, timings and markers come over the **serial console log** |
| submission | a k8s manifest of a KubeVirt-class VM kind (a bare `VirtualMachineInstance`; `VirtualMachine` is refused by R3) | the image ships as a containerDisk referenced by `@sha256` |

Four probes run inside the image:

| # | probe | how it acts | what it reads |
|---|-------|-------------|---------------|
| P1 | SDDM greeter login | keys over VNC (an RFB client on the `vnc` subresource) | `vnc/screenshot` before and after; the `sddm` journal and the `el.session` marker on serial |
| P2 | wallpaper as Plasma loads it | none (autologin) | plasmashell journal and `plasma-org.kde.plasma.desktop-appletsrc` on serial; `vnc/screenshot` after `el.settled` |
| P3 | plymouth splash | none | a timestamped `vnc/screenshot` series polled from VMI `Scheduled`, plus the serial log |
| P4 | boot timing | none (autologin) | `systemd-analyze time` / `blame` / `critical-chain` on serial |

## (a) Base: Debian trixie, amd64

**Decision: Debian trixie**, from the same `debian@sha256:a99cfc51…` lineage that
`oci/Containerfile` already pins. Its apt sources point at `snapshot.debian.org`
at one fixed timestamp.

Reasons, read from the tree:

- **The route users take is already a Debian route.** `make_deb.py` builds
  `el-openglo-themes_<ver>_all.deb`. Its root helpers are also Debian-specific:
  `el-openglo-plymouth` selects the theme through `update-alternatives
  default.plymouth` and then runs `update-initramfs -u`, which is the
  initramfs-tools path. On any other base, P3 would test a selection route that no
  user of the package runs.
- **Trixie has everything we need in stock packages:** Plasma 6 (`kde-plasma-desktop`,
  `plasma-workspace`), `sddm` with `sddm-greeter-qt6` (which the W66 themes need,
  `QtVersion=6`), `plymouth` plus `plymouth-themes`, and systemd. We compile
  nothing.
- **Reproducibility is reachable.** `snapshot.debian.org` plus a fixed timestamp
  closes the gap that `catalog/host.json` names in its caveats ("can be IDENTIFIED
  but not REBUILT"). The render image can take the same fix later.

Residue, kept on purpose:

- **Gentoo** (`overlay/x11-themes/el-openglo-9999.ebuild`, W12). The ebuild
  installs the same tree, because its `src_install` is `make_deb.py --stage
  "${ED}"`. But a Plasma 6 Gentoo guest means hours of compiling or a binpkg host.
  The plymouth helper now has a `plymouth-set-default-theme -R` route (see the gaps),
  so Gentoo can become a second image. It stays out of the first image.
- **Fedora KDE.** It ships Plasma 6, SDDM and plymouth, but we would need an RPM
  packager, and none exists yet.
- **Arch.** It rolls, so a snapshot at one timestamp means the Arch Linux Archive, and
  there is no packager for it. It adds nothing that Debian lacks.

## (b) Theme ingress: the `.deb`, installed by `apt`

**Decision:** `make_deb.build()` produces the `.deb`, and the image installs it with
`apt-get install ./el-openglo-themes_<ver>_all.deb`. The helpers then run exactly as
`CONTROL`/`POSTINST` tell a user to run them.

- **We do not copy files.** Copying skips `POSTINST` (`fc-cache`,
  `kbuildsycoca6`) and the dependency resolution on `plasma-workspace`, and those
  are the parts that differ from the tree.
- **We do not use the ebuild on a Debian base.** The ebuild wraps the same
  `stage()` output, so as long as `check_ebuild.py` holds, the payload is the same.
  What differs is only the packager, and the packager is what P3 exercises.
- **The image records the `.deb`'s sha256 next to its own digest** (see (c)).
  A probe result then names both the host and the theme build it measured.

## (c) Build and digest

The disk ships as a **containerDisk**: an OCI image containing `/disk/guest.qcow2`,
owned by 107:107. We chose it over a DataVolume for three reasons:

1. **It reuses W61's digest machinery unchanged.** buildkitd builds the OCI image
   and writes `containerimage.digest` to `--metadata-file`. That is a witness from
   a different party than the builder, exactly as `catalog/host.json` requires.
   A DataVolume qcow2 has no such witness; we would have to hash it ourselves.
2. **The manifest references it by `@sha256`, and the result is keyed by that digest.**
   luthen's proposed R8 (Q7) would require the digest at admission. Either way the
   digest is the identity.
3. **It is throwaway by construction.** A containerDisk is ephemeral per VMI, which
   fits a 30-minute TTL.

Build pipeline (a recipe to write later; nothing here has been built):

1. `mmdebstrap` trixie from `snapshot.debian.org/archive/debian/<T>`, with
   `SOURCE_DATE_EPOCH=<T>`, into a raw image (kernel, grub, initramfs-tools).
2. Inside the chroot: install the package set from (e), then
   `apt-get install ./el-openglo-themes_*.deb`, then run the root helpers (see (d)),
   then install the serial reporter from (f). `qemu-guest-agent` is dropped because
   nothing can reach it: there is no QMP and no guest-agent client.
3. Write `/etc/el-openglo-guest.json`: the snapshot timestamp `T`, the `.deb` name
   and sha256, `git rev-parse HEAD`, and `dpkg-query` output. This follows
   Containerfile's provenance idea (`/etc/el-openglo-packages.tsv`). The reporter
   emits this file at boot as the `el.ident` record, so the serial log names its own
   image.
4. `qemu-img convert` to qcow2, then build `FROM scratch` / `ADD guest.qcow2 /disk/`
   under buildctl with `--metadata-file`.
5. Record **`catalog/guest-image.json`**, a sibling of `host.json` with the same
   keys: `ref`, `digest` (from buildkitd), `config_digest`, `source`, `base`, plus
   `snapshot`, `deb_sha256` and `git_rev`.

Every probe result must carry `guest_digest` and `deb_sha256`. A result without
them is withheld, not passed. host.json applies the same rule to renders, and
`check_action_key.py` is the existing reader to extend.

## (d) Login and plymouth selection, per probe

We build one image and choose the variant at boot with a kernel cmdline, not at
build time. There are two sddm.conf.d fragments, and a cmdline flag
(`el.probe=greeter|autologin`) picks one of them, so the digest stays the same
across probes. The flag reaches the guest as `kernelArgs` only under direct-kernel boot.
With a containerDisk that boots through grub, a systemd credential in the manifest
(SMBIOS `io.systemd.credential`) carries it instead. The first boot settles which of the
two the surface lets through (⟐W71e).

| probe | login | why |
|-------|-------|-----|
| P1 SDDM | **greeter**, selected by `el-openglo-sddm` (the W66 theme) | the greeter *is* the thing under test. A test user `probe` with a known password is typed as **RFB key events over the `vnc` subresource** (`virtctl vnc --proxy-only` + an RFB client). Screenshots come from `GET …/vnc/screenshot`. SDDM's own `sddm` journal lines and the `el.session` marker come out on serial, so "login succeeded" is a guest fact rather than a pixel diff. |
| P2 wallpaper | **autologin** `[Autologin] User=probe Session=plasma` | the greeter is not under test, and autologin keeps that variable out. `el-openglo-apply EL-Openglo` + `el-openglo-live` run once as `probe` from a first-login autostart entry. That is the user's own route; the rc files are not pre-seeded. The reporter emits the plasmashell journal and the appletsrc on `el.settled`, and the harness takes a `vnc/screenshot` when that record appears. |
| P3 plymouth | **autologin** (plymouth ends before SDDM, so either works) | selection happens at image build: `el-openglo-plymouth EL-Openglo` runs in the chroot. That is the user's route (alternatives + `update-initramfs -u`). Cmdline: `quiet splash plymouth.ignore-serial-consoles console=tty0 console=ttyS0`, because with a serial console active plymouth otherwise falls back to details/text. **This has to be checked on the first boot.** The series is `vnc/screenshot` polled at a fixed interval from VMI `Scheduled`, one timestamped PNG per poll. Frames from before the VNC server is live are recorded as withheld. The VM needs a DRM device (KubeVirt's default VGA gives bochs-drm/simpledrm), otherwise the frames show a text console. |
| P4 timing | **autologin** | `systemd-analyze` reports only once boot has finished. A greeter waiting for input would make "finished" mean "sitting at a login screen". The reporter emits the three outputs on `el.session`. Run it once with `splash` and once without, so the splash's cost is measured as a difference rather than assumed. |

Every probe has to fit in the 30 min TTL: boot, the probe itself, and the artifact copy
(the harness reads `guest-console-log` before deletion; the log dies with the object).
The reporter's `el.done` record (f) tells the harness it can stop early. **Estimate:**
a cold trixie boot to a Plasma session on 1 vCPU with llvmpipe takes about 1–3 min, so
the TTL is not the binding limit. Memory is.

## (e) Memory budget (every figure is an ESTIMATE unless it says READ)

### The envelope

**READ:** KubeVirt v1.9.0, `pkg/hypervisor/kvm/hypervisorbackend.go` (`GetMemoryOverhead`),
read 2026-09-23:

| term | value | applies to us |
|------|-------|---------------|
| virt-launcher-monitor + virt-launcher + virtlogd + virtqemud + qemu (fixed) | 25 + 100 + 25 + 40 + 30 = **220 Mi** | yes |
| per vCPU | 8 Mi | 1 vCPU: 8 Mi |
| IOThread | 8 Mi | yes |
| graphics device (autoattach on or unset) | 32 Mi | **yes**: VNC needs it |
| pagetables | guest RAM / 512 | ~1.4 Mi at 700 Mi |
| CPU dedicated **or QoS Guaranteed** | 100 Mi | **unknown**: see below |
| TPM / SEV / exec probes / VFIO | 53 / 256 / 100+ / 1 Gi | no: leave them off |

Plus the `guest-console-log` sidecar at **35 M** (luthen's readings §6, MEASURED/INFERRED there).

- Burstable QoS: 220 + 8 + 8 + 32 + ~1.4 + 35 ≈ **305 Mi**, which leaves **≈ 719 Mi of guest RAM**.
- If the pod is QoS **Guaranteed** (luthen's LimitRange sets memory request = limit; the
  pod is Guaranteed only if CPU also has limit = request, and luthen proposes no CPU
  limit): **≈ 405 Mi**, which leaves **≈ 619 Mi**. Which one applies depends on luthen's
  final LimitRange, and F0 measures it. **Plan for ~620 Mi and hope for ~700.**

### Per-probe estimates (guest RSS at the probe's point; ESTIMATES, from typical Debian/KDE figures, not measured here)

| probe | stops at | est. guest memory in use | fits ~620–700 Mi? |
|-------|----------|--------------------------|-------------------|
| P3 plymouth only | initrd + early userspace; plymouthd with our two-step theme, framebuffer | **150–250 Mi** (kernel + initramfs unpack + page cache + plymouthd). The initramfs is transient but has to fit unpacked | **yes** |
| P1 SDDM greeter | `graphical.target`; sddm + `sddm-greeter-qt6` on X11 (Xorg) or a kwin_wayland/weston greeter, rendering with llvmpipe | **350–550 Mi** | **likely**, if trimmed |
| P2 / P4 full Plasma 6 session | kwin_wayland + plasmashell + kded6 + xdg-desktop-portal-kde + powerdevil + … with llvmpipe | stock: **1.2–1.8 Gi**. Trimmed: **700–900 Mi** | **likely NOT**, even trimmed |

### The cheapest configuration that could fit

- **Package set:** `kde-plasma-desktop` with `--no-install-recommends`, then `sddm sddm-greeter-qt6
  plymouth` (not `task-kde-desktop`). No Discover, no KDE Connect, no printing, no
  PackageKit, no NetworkManager applet (systemd-networkd, or no network at all:
  the probes need none).
- **Session trims** (config in the image, not code): Baloo off (`balooctl6 disable` /
  `[Basic Settings] Indexing-Enabled=false`); no akonadi (it is not pulled in without PIM
  apps, so assert it is absent); disable `kded6` modules we do not need, the
  `plasma-discover-notifier`, `kaccess`, `xembedsniproxy`, `baloorunner`; `kwin`
  with animations off (it saves CPU, not memory).
- **In-guest zram:** `systemd-zram-generator`, `zram-size = ram / 2`, zstd. Plasma's cold
  pages (QML caches, unused libs) compress about 3:1, which **could** buy ~150–250 Mi
  of effective headroom. The cost is CPU, which is unbounded on luthen (no CPU limit).
  It is the one trim that could carry P2/P4 over the line, and it is the reason those
  probes are "likely NOT" and not "cannot".
- **Greeter on a minimal compositor (P1):** SDDM 0.21 can run its Wayland greeter under
  `weston` (`[General] DisplayServer=wayland`, `[Wayland] CompositorCommand=weston
  --shell=kiosk`). That avoids Xorg (~60–100 Mi estimated) and is closer to what Plasma 6
  users get than Xorg is. Residue: if a user's greeter runs on X11, P1 on weston is a
  different route. The first measurement decides whether the saving is worth it.
- **Trimmed initramfs (P3):** `MODULES=dep` in `/etc/initramfs-tools/initramfs.conf`
  (it is built inside the VM's own device set) and `COMPRESS=zstd`. That cuts the unpacked
  initramfs from roughly 60–100 Mi to 20–40 Mi (estimate). The plymouth theme still has to
  be inside it; `update-initramfs -u` from the helper does that.
- **Kernel cmdline that stops at a target:** P3 needs neither SDDM nor Plasma. With
  `systemd.unit=el-probe-splash.target` (a target in the image that is `multi-user.target`
  minus the display manager, plus the reporter), P3 stays in the ~200 Mi range whatever
  P2 needs. P1 uses `graphical.target` with the greeter; P2/P4 use `graphical.target`
  with autologin. All of this is selected by cmdline or credential, so it is one digest.
- **Guest memory request:** set `spec.domain.memory.guest` explicitly (for example 700Mi
  under Burstable, 616Mi under Guaranteed) so the envelope is computed and not guessed.
  Overshooting is refused at admission, which is itself a clean reading.

### What probably cannot fit, and the measurable ask

- **P3 fits and P1 probably fits.** P2 and P4 need a full Plasma session, and they are the
  probes likely to fail inside 1 GiB. The failure would show as an OOM in the guest
  (`el.oom` on serial, see (f)) or a session that never emits `el.session` before the TTL.
- **The ask, when F0 shows it:** an environment of **1.5 GiB** (≈ 1.1–1.2 Gi of guest RAM
  after the ~305–405 Mi overhead), which a trimmed Plasma 6 session with zram should clear
  with margin. The evidence we would hand the operator is a P2 run at 1 GiB with its
  `el.mem` samples (f): peak `MemAvailable`, zram ratio, and the OOM or timeout record.
  That is a measured shortfall, not a guess.
- **P4 alone** could be partly salvaged at 1 GiB by measuring to `graphical.target` with
  the greeter (P1's config). That times the boot, not the session, and it would be
  recorded under that name, not as P4.

## (f) Serial-console protocol (`el-serial/1`): one spec for the guest unit and our reader

The only way out of the guest is ttyS0, captured by `guest-console-log` from t=0 and read
with `kubectl logs … -c guest-console-log`. The kernel, systemd, plymouth and getty all
write to that same stream, so our records have to be recoverable from the noise.

**Framing.** A record is exactly one line:

```text
@@EL1 SEQ KIND JSON\r\n
```

- `@@EL1` starts the line. `SEQ` is a decimal counter starting at 0 for each boot, so
  the reader can detect a lost or interleaved record as a gap.
- `KIND` is `[a-z.]+`. `JSON` is a single-line JSON object (no raw newline; UTF-8;
  keys sorted). Every object carries `"t"` (CLOCK_MONOTONIC in seconds, float, from
  `/proc/uptime`) and `"boot"` (`/proc/sys/kernel/random/boot_id`).
- **Lines longer than 1024 bytes are chunked**, because consoles can interleave with kernel
  printk inside a long line. A large payload (a journal, appletsrc) is emitted as
  `blob.part` records `{"id","n","of","b64"}`, 768 bytes of base64 each, closed by
  `blob.end {"id","sha256","bytes","kind"}`. The reader reassembles, checks the sha256,
  and treats a gap or a mismatch as **withheld**, never as partial data.
- The emitter writes to `/dev/ttyS0` directly (not through the journal's console
  forwarding), taking an `flock` on `/run/el-serial.lock` so its records never
  interleave with each other.

**Kinds** (the guest emits these; the reader knows exactly these):

| kind | when | payload |
|------|------|---------|
| `el.ident` | reporter start (`sysinit.target`) | contents of `/etc/el-openglo-guest.json`, `/proc/cmdline`, `el.probe` |
| `el.mem` | every 5 s until `el.done` | `MemTotal`, `MemAvailable`, `SwapTotal`, `SwapFree`, zram `orig_data_size`/`compr_data_size` |
| `el.oom` | a kernel OOM kill (`journalctl -k -f` match) | victim comm, pid, `MemAvailable` at the time |
| `el.greeter` | `sddm.service` active, and the greeter process present | greeter pid, the `Current` theme from the resolved sddm config |
| `el.session` | `graphical-session.target` reached for user `probe` (a `--user` unit) | uid, `XDG_SESSION_TYPE` |
| `el.settled` | plasmashell has a stable window list for 5 s after `el.session`, or a 90 s cap (recorded as `"capped":true`) | `capped` |
| `el.analyze` | after `el.session` (P4), or after `el.greeter` in the P1 fallback | blob ids of `systemd-analyze time`, `blame`, `critical-chain` output |
| `el.journal` | at `el.settled` / `el.greeter` | blob ids of `journalctl -b -o json -u sddm`, `--user -u plasma-plasmashell`, `-u plymouth-*` |
| `el.file` | at `el.settled` (P2) | blob id of `~probe/.config/plasma-org.kde.plasma.desktop-appletsrc` |
| `el.done` | the probe has emitted everything | `{"probe", "records": <count>}`, which the reader checks against what it received |

**Guest side:** `el-serial.service` (system, `DefaultDependencies=no`, after
`systemd-journald.service`) runs `/usr/libexec/el-openglo/el-serial`, a small POSIX-sh
and `jq` emitter (no Python in the guest) that owns the framing, plus a user unit
`el-serial-session.service` `WantedBy=graphical-session.target` that asks it, over a
FIFO in `/run`, to emit the session-side records. Both ship in the image, not in the `.deb`:
they are probe machinery, not theme.

**Reader side:** a `scripts/read_serial.py` (to write, with `--selftest` over a captured
log containing interleaved printk, a split record, and a bad sha) emits `--json` facts:
records by kind, sequence gaps, reassembled blobs, withheld reasons. A policy
(`policy/serial.rego`) decides what each probe requires: for example P2 needs `el.ident`,
`el.session`, `el.settled`, `el.file` and `el.done` with no gap. A log with no
`el.ident` is an empty population and is refused.

## What el-openglo does not yet emit

These were checked against `emitters.ROLES`, `make_deb.stage()`, `make_plymouth.py`
and `make_sddm.py` before being written down as gaps:

- **Already covered, and not a gap:**
  - Plymouth themes: `make_plymouth` is in ROLES, and `stage()` renders it into
    `/usr/share/plymouth/themes/el-openglo-<Variant>/`.
  - The SDDM greeter: `make_sddm`, W66, staged into `/usr/share/sddm/themes`.
- **G1–G3 (selecting the W66 greeter; the portable plymouth theme filename; the plymouth
  helper failing loudly) have been fixed on main.** Their status is not recorded here:
  it is the exit code of `scripts/opa_gate.py root_helpers`, where
  `scripts/check_root_helpers.py` runs both helpers against a scratch root with stubbed
  tools and `policy/root_helpers.rego` decides. The selection routes the gate exercises
  are `el-openglo-sddm VARIANT` (a drop-in with `Current=el-openglo-<slug>`, undone by
  `--breeze`) and `el-openglo-plymouth [--no-initramfs] VARIANT` (the alternatives route,
  else `plymouth-set-default-theme -R`). What the gate does not cover is whether plymouth
  *draws* the theme at boot; that is P3's question.
- **G4: no guest-image recipe or record.** `oci/guest/` (the mmdebstrap script plus
  the containerDisk Containerfile) and `catalog/guest-image.json` do not exist.
  Both are W71's build step.
- **G5: no probe-side reader of the guest digest.** `check_action_key.py` reads
  `host.json` only. It needs to read the guest identity for probe results in the
  same way. The `el.ident` record (f) is where a probe result gets it.
- **G6: no serial reporter or reader.** The guest units and `scripts/read_serial.py` +
  `policy/serial.rego` from (f) do not exist.
- **G7: no RFB client in the harness.** P1 needs VNC key events. We have no QMP, so
  vncdo, or a websocket RFB client on the `vnc` subresource, has to be chosen and pinned.

## Next steps

- ⟐W71a / ⟐W71b (G1–G3): carried by the `root_helpers` gate; nothing more to do here.
- ⟐W71c: write `oci/guest/` with the (e) package set and trims, and a `--selftest` that
  proves the build refuses an unpinned snapshot. Build it once and record
  `catalog/guest-image.json` with `adopted:false` until a probe has run.
- ⟐W71d: extend `check_action_key` (G5) so a probe result without
  `guest_digest` and `deb_sha256` is withheld.
- ⟐W71f: the `el-serial/1` emitter and units, plus `read_serial.py` / `policy/serial.rego` (G6).
  They are testable on the host now, against a synthetic log.
- ⟐W71g: pick and pin the RFB client (G7).
- ⟐W71e: on luthen's first VMI (F0): measure the real launcher overhead and the QoS
  class (Burstable ~305 Mi vs Guaranteed ~405 Mi); confirm the containerDisk choice, the
  DRM/serial cmdline (P3), and whether `kernelArgs` or an SMBIOS credential carries
  `el.probe`.
- ⟐W71h: run P3, then P1, at 1 GiB. Run P2 at 1 GiB with `el.mem` sampling. If it OOMs
  or times out, hand the operator that log together with the 1.5 GiB ask from (e).
