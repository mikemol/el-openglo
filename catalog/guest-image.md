# The guest image (W71): scoping

luthen-observability will run throwaway VMs through k8s: a submitted manifest, a
KubeVirt VM for boot and GUI work, a plain Pod for userspace work. **That surface is
not ready yet.** luthen has said the guest image is ours to build. This document
decides what the image is, so that the image exists when the surface does.

Four probes run inside it:

| # | probe | what it reads |
|---|-------|---------------|
| P1 | SDDM greeter login | QMP `send-key`; screendump before and after |
| P2 | wallpaper as Plasma loads it | plasmashell journal, `plasma-org.kde.plasma.desktop-appletsrc` naming the mounted plugin |
| P3 | plymouth splash | a timestamped QMP `screendump` series, plus the serial log |
| P4 | boot timing | `systemd-analyze time` / `blame` / `critical-chain` |

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
  "${ED}"`. But a Plasma 6 Gentoo guest means hours of compiling or a binpkg host,
  and Gentoo has no stock route for the `el-openglo-plymouth` helper (no
  alternatives, and dracut instead of initramfs-tools). It becomes a second image
  once the plymouth gap below is closed. It stays out of the first image.
- **Fedora KDE.** It ships Plasma 6, SDDM and plymouth, but we would need an RPM
  packager that does not exist yet, and its plymouth route is
  `plymouth-set-default-theme -R`, which our theme layout does not satisfy (see
  G2).
- **Arch.** It rolls, so a snapshot at one timestamp is the Arch Linux Archive, and
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

The KubeVirt surface is not ready, so the plan uses its own vocabulary: the disk
ships as a **containerDisk** (an OCI image with `/disk/guest.qcow2`, owned by
107:107). That form is chosen over a DataVolume for three reasons:

1. **It reuses W61's digest machinery unchanged.** buildkitd builds the OCI image
   and writes `containerimage.digest` to `--metadata-file`, which is a witness from
   a different party than the builder, exactly as `catalog/host.json` requires.
   A DataVolume qcow2 has no such witness; we would have to hash it ourselves.
2. **The manifest can reference it by `ref`, and the result is keyed by `digest`.**
   This follows the ref/digest separation in host.json (CRI resolves the ref; the
   digest is the identity).
3. **It is throwaway by construction.** A containerDisk is ephemeral per VMI, which
   is what "throwaway VM" asks for.

Build pipeline (a recipe to write later; nothing here has been built):

1. `mmdebstrap` trixie from `snapshot.debian.org/archive/debian/<T>`, with
   `SOURCE_DATE_EPOCH=<T>`, into a raw image (kernel, `systemd-boot` or grub,
   initramfs-tools).
2. Inside the chroot: install `kde-plasma-desktop sddm plymouth qemu-guest-agent`,
   then `apt-get install ./el-openglo-themes_*.deb`, then run the root helpers (see (d)).
3. Write `/etc/el-openglo-guest.json`: the snapshot timestamp `T`, the `.deb` name
   and sha256, `git rev-parse HEAD`, and `dpkg-query` output. This follows
   Containerfile's provenance idea (`/etc/el-openglo-packages.tsv`).
4. `qemu-img convert` to qcow2, then run `FROM scratch` / `ADD guest.qcow2 /disk/`
   under buildctl with `--metadata-file`.
5. Record **`catalog/guest-image.json`**, a sibling of `host.json` with the same
   keys: `ref`, `digest` (from buildkitd), `config_digest`, `source`, `base`, plus
   `snapshot`, `deb_sha256` and `git_rev`.

Every probe result must carry `guest_digest` and `deb_sha256`. A result that lacks
them is a withheld fact, not a pass. It is the same rule host.json applies to
renders, and `check_action_key.py` is the existing reader to extend.

## (d) Login and plymouth selection, per probe

We build one image and select the variant at boot with a kernel cmdline, not at
build time. There are two sddm.conf.d fragments, and one of them is chosen by a
systemd credential or cmdline flag (`el.probe=greeter|autologin`), so the digest
stays the same across probes.

| probe | login | why |
|-------|-------|-----|
| P1 SDDM | **greeter**, `[Theme] Current=el-openglo-openglo` (the W66 theme) | the greeter *is* the thing under test. A test user `probe` with a known password is typed with QMP `send-key`. |
| P2 wallpaper | **autologin** `[Autologin] User=probe Session=plasma` | the greeter is not under test, and autologin keeps the variable out. `el-openglo-apply EL-Openglo` + `el-openglo-live` run once as `probe` from a first-login autostart entry, which is the user's own route, not pre-seeded rc files. The probe then reads the journal and appletsrc. |
| P3 plymouth | either (plymouth ends before SDDM); use **autologin** | selection happens at image build: `el-openglo-plymouth EL-Openglo` runs in the chroot, which is the user's route (alternatives + `update-initramfs -u`). Cmdline: `quiet splash plymouth.ignore-serial-consoles console=ttyS0`, because with a serial console active plymouth otherwise falls back to details/text. **This needs to be verified on the first boot.** The VM needs a DRM device (KubeVirt's default VGA/bochs-drm gives simpledrm/bochs), or the screendumps show a text console. |
| P4 timing | **autologin** | `systemd-analyze` reports only after boot finishes (`graphical.target`). A greeter waiting for input makes "finished" mean "sitting at a login screen". Run it once with and once without `splash`, so the splash's own cost is a difference and not something assumed. |

## What el-openglo does not yet emit

These were checked against `emitters.ROLES`, `make_deb.stage()`, `make_plymouth.py`
and `make_sddm.py` before being written down as gaps:

- **Already covered, and not a gap:**
  - Plymouth themes: `make_plymouth` is in ROLES, and `stage()` renders it into
    `/usr/share/plymouth/themes/el-openglo-<Variant>/`.
  - The SDDM greeter: `make_sddm`, W66, staged into `/usr/share/sddm/themes`.
  - The plymouth selection helper: `el-openglo-plymouth`.
- **G1: nothing selects the W66 greeter.** `el-openglo-sddm` still points stock
  Breeze at a wallpaper. Nothing writes `[Theme] Current=el-openglo-<slug>`.
  P1 needs a selection route a user would run, either a mode on the helper or a
  second helper. Otherwise the image hand-writes sddm.conf.d, which violates (b).
- **G2: the plymouth theme layout is Debian-only.** The directory is
  `el-openglo-<Variant>` but the file is `el-openglo.plymouth`.
  `plymouth-set-default-theme` (Fedora, Arch, Gentoo) expects `<name>/<name>.plymouth`,
  so the theme is only selectable through Debian alternatives. The fix is to emit
  `el-openglo-<Variant>.plymouth`. That fix also unblocks the Gentoo residue.
- **G3: the plymouth helper hides failure.** Every `update-alternatives` call
  ends in `|| true`, and a missing `update-initramfs` is skipped silently. In the
  image build a failed selection would boot the stock splash and P3 would measure
  the wrong theme. The helper should exit non-zero on a failed selection, and the
  build should assert `plymouth-set-default-theme` or
  `readlink /etc/alternatives/default.plymouth`.
- G1-G3 are measured by `scripts/opa_gate.py root_helpers`
  (`check_root_helpers.py` runs both helpers against a scratch root and
  `policy/root_helpers.rego` decides), so whether each gap is open is that gate's
  exit code. It is not recorded here. The selection routes it checks are
  `el-openglo-sddm VARIANT` (a drop-in with `Current=el-openglo-<slug>`, undone
  by `--breeze`) and `el-openglo-plymouth [--no-initramfs] VARIANT` (the
  alternatives route, else `plymouth-set-default-theme -R`).
- **G4: no guest-image recipe or record.** `oci/guest/` (the mmdebstrap script plus
  the containerDisk Containerfile) and `catalog/guest-image.json` do not exist.
  Both are W71's build step.
- **G5: no probe-side reader of the guest digest.** `check_action_key.py` reads
  `host.json` only. It needs to read the guest identity for probe results in the
  same way.

## Next steps

- ⟐W71a: close G2 and G3 in `make_plymouth` and the helper (theme filename, fail
  loudly). This is testable on the host now, with no VM.
- ⟐W71b: close G1 with an SDDM selection mode for the W66 theme.
- ⟐W71c: write `oci/guest/` and a `--selftest` that proves the build refuses an
  unpinned snapshot. Build it once and record `catalog/guest-image.json` with
  `adopted:false` until a probe has run.
- ⟐W71d: extend `check_action_key` (G5) so a probe result without
  `guest_digest` and `deb_sha256` is withheld.
- ⟐W71e: when luthen's surface is ready, confirm the containerDisk vs DataVolume
  choice and the DRM/serial cmdline assumption (P3) on the first boot.
