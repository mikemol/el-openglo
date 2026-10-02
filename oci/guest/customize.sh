#!/bin/sh
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
#
# customize.sh ROOT DEB - mmdebstrap --customize-hook for the guest image (W235).
# Runs on the HOST with the chroot at ROOT (catalog/guest-image.md (c) step 2-3):
# install our .deb the user's way (apt, so POSTINST runs), select the plymouth theme
# by the user's route, apply the (e) trims, assert the absent set, and write the
# provenance file the reporter emits as el.ident.
#
# Weakness: run only by the image build (the mmdebstrap command
# scripts/check_guest_recipe.py --plan prints; a heavy run). The recipe gate checks
# the pins, not this script's effect on a real chroot.
set -eu
ROOT=$1
DEB=$2
SNAPSHOT=$3
GIT_REV=$4

cp "$DEB" "$ROOT/tmp/el-openglo.deb"
chroot "$ROOT" apt-get install -y --no-install-recommends /tmp/el-openglo.deb
rm -f "$ROOT/tmp/el-openglo.deb"

# P3: the plymouth theme is selected at build, through the user's helper (d)
chroot "$ROOT" el-openglo-plymouth EL-Openglo

# trims (e): baloo off, zram, a dep-only zstd initramfs
mkdir -p "$ROOT/etc/xdg"
printf '[Basic Settings]\nIndexing-Enabled=false\n' > "$ROOT/etc/xdg/baloofilerc"
printf '[zram0]\nzram-size = ram / 2\ncompression-algorithm = zstd\n' > "$ROOT/etc/systemd/zram-generator.conf"
sed -i 's/^MODULES=.*/MODULES=dep/; s/^#\?COMPRESS=.*/COMPRESS=zstd/' "$ROOT/etc/initramfs-tools/initramfs.conf"
chroot "$ROOT" update-initramfs -u

# the probe user (P1 types this password over RFB; it guards nothing: the VM is throwaway)
chroot "$ROOT" useradd -m -s /bin/sh probe
echo 'probe:probe' | chroot "$ROOT" chpasswd

# the serial reporter (f, G6; W237): writer, spec, reporter, both units. The session
# side runs as `probe`, so ttyS0 and the shared lock/SEQ files are group dialout.
GUEST=$(dirname "$0")/../../guest
install -D -m 0755 "$GUEST/el-serial-emit.sh" "$ROOT/usr/bin/el-serial-emit"
install -D -m 0755 "$GUEST/el-reporter.sh" "$ROOT/usr/libexec/el-openglo/el-reporter"
install -D -m 0644 "$GUEST/el-serial-spec.json" "$ROOT/usr/share/el-openglo/el-serial-spec.json"
install -D -m 0644 "$GUEST/el-serial.service" "$ROOT/etc/systemd/system/el-serial.service"
install -D -m 0644 "$GUEST/el-serial-session.service" "$ROOT/etc/systemd/user/el-serial-session.service"
printf 'f /run/el-serial.lock 0660 root dialout -\nf /run/el-serial.seq 0660 root dialout -\nf /run/el-serial.probe 0664 root dialout -\n' \
	> "$ROOT/etc/tmpfiles.d/el-serial.conf"
chroot "$ROOT" usermod -aG dialout probe
chroot "$ROOT" systemctl enable el-serial.service
chroot "$ROOT" systemctl --global enable el-serial-session.service

# provenance (c) step 3: the reporter emits this as el.ident
DEB_SHA=$(sha256sum < "$DEB")
chroot "$ROOT" dpkg-query -W -f '${Package}\t${Version}\n' > "$ROOT/etc/el-openglo-packages.tsv"
jq -n --arg snapshot "$SNAPSHOT" --arg deb "$(basename "$DEB")" --arg sha "${DEB_SHA%% *}" --arg rev "$GIT_REV" \
	'{snapshot: $snapshot, deb: $deb, deb_sha256: $sha, git_rev: $rev}' > "$ROOT/etc/el-openglo-guest.json"
