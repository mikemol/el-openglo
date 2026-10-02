#!/bin/sh
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
#
# el-reporter - the guest's serial REPORTER (catalog/guest-image.md (f), G6; W237).
# POSIX sh + jq + coreutils + procps; every record goes through el-serial-emit,
# which validates it against guest/el-serial-spec.json. There is no Python in the
# guest (operator ruling, guest-image.md (f)).
#
#   el-reporter system    el-serial.service: el.ident, el.mem, then the probe's
#                         system-side tail (P3: plymouth; P1/P4g: the greeter)
#   el-reporter session   el-serial-session.service (user): el.session, el.mem
#                         samples, el.settled, the session tail (P2/P4)
#
# ⚑ IT REPORTS WHAT IT OBSERVES. Which kinds a probe REQUIRES is policy/serial.rego's;
# this file only knows which side of the boot (system / greeter / session) a probe
# ends on - the image's own wiring, guest-image.md (d) - and emits what is there.
# A probe the table does not name ends on the system side with el.done, so the
# policy's S2 denies it by name rather than the harness waiting out the TTL.
#
# Every path is overridable (EL_*) so a host bundle can drive it on stub files.
#
# Weakness: the settle rule (plasmashell up, then EL_SETTLE_S quiet seconds, capped
# at EL_SETTLE_CAP_S) is a guess until the first guest boot (W239) measures it.
set -eu

EMIT=${EL_EMIT:-el-serial-emit}
CMDLINE=${EL_CMDLINE_FILE:-/proc/cmdline}
MEMINFO=${EL_MEMINFO_FILE:-/proc/meminfo}
ZRAM=${EL_ZRAM_MM_STAT:-/sys/block/zram0/mm_stat}
GUEST_JSON=${EL_GUEST_JSON:-/etc/el-openglo-guest.json}
CRED=${EL_PROBE_CREDENTIAL:-${CREDENTIALS_DIRECTORY:-/nonexistent}/el.probe}
APPLETSRC=${EL_APPLETSRC:-$HOME/.config/plasma-org.kde.plasma.desktop-appletsrc}
SDDM_CONF_DIR=${EL_SDDM_CONF_DIR:-/etc/sddm.conf.d}
SETTLE_S=${EL_SETTLE_S:-10}
SETTLE_CAP_S=${EL_SETTLE_CAP_S:-300}
WAIT_S=${EL_WAIT_S:-600}
PROBE_FILE=${EL_PROBE_FILE:-${EL_SERIAL_RUN:-/run}/el-serial.probe}

# the probe: an SMBIOS credential wins (containerDisk boots through grub), else the
# cmdline's el.probe= (direct-kernel boot) - guest-image.md (d); W239 settles which
probe() {
	# the session side cannot read the system credential: the system side records it
	if [ -r "$PROBE_FILE" ]; then
		head -n1 "$PROBE_FILE"
		return
	fi
	if [ -r "$CRED" ]; then
		head -n1 "$CRED"
		return
	fi
	read -r line < "$CMDLINE"
	# word-split on purpose: cmdline arguments are space-separated words
	for w in $line; do
		case "$w" in el.probe=*) echo "${w#el.probe=}"; return ;; esac
	done
	echo unknown
}

kb() { awk -v k="$1:" '$1 == k { print $2; exit }' "$MEMINFO"; }

mem() {
	orig=0 compr=0
	if [ -r "$ZRAM" ]; then
		read -r orig compr _ < "$ZRAM"
	fi
	"$EMIT" frame el.mem "$(jq -cn --argjson t "$(kb MemTotal)" --argjson a "$(kb MemAvailable)" \
		--argjson st "$(kb SwapTotal)" --argjson sf "$(kb SwapFree)" --argjson o "$orig" --argjson c "$compr" \
		'{mem_total_kb: $t, mem_available_kb: $a, swap_total_kb: $st, swap_free_kb: $sf,
		  zram_orig_bytes: $o, zram_compr_bytes: $c}')"
}

# blob LABEL CMD... : capture a command's output to a temp file, send it, print the id
blob() {
	label=$1
	shift
	f=$(mktemp)
	"$@" > "$f" 2>&1 || true
	id=$("$EMIT" blob "$label" "$f")
	rm -f "$f"
	echo "$id"
}

journals() {
	sd=$(blob journal.sddm journalctl -b -o json -u sddm)
	ps=$(blob journal.plasmashell journalctl -b -o json --identifier plasmashell)
	pl=$(blob journal.plymouth journalctl -b -o json -u plymouth-start -u plymouth-quit -u plymouth-quit-wait)
	"$EMIT" frame el.journal "$(jq -cn --arg a "$sd" --arg b "$ps" --arg c "$pl" \
		'{sddm: $a, plasmashell: $b, plymouth: $c}')"
}

analyze() {
	t=$(blob analyze.time systemd-analyze time)
	b=$(blob analyze.blame systemd-analyze blame)
	c=$(blob analyze.critical_chain systemd-analyze critical-chain)
	"$EMIT" frame el.analyze "$(jq -cn --arg a "$t" --arg b "$b" --arg c "$c" \
		'{time: $a, blame: $b, critical_chain: $c}')"
}

# wait_for SECONDS CMD... : poll CMD once a second until it succeeds; 1 on timeout
wait_for() {
	n=$1
	shift
	while [ "$n" -gt 0 ]; do
		"$@" > /dev/null 2>&1 && return 0
		sleep 1
		n=$((n - 1))
	done
	return 1
}

system() {
	rm -f "$PROBE_FILE"
	p=$(probe)
	echo "$p" > "$PROBE_FILE"
	"$EMIT" frame el.ident "$(jq -cn --slurpfile g "$GUEST_JSON" --arg c "$(cat "$CMDLINE")" --arg p "$p" \
		'{guest: $g[0], cmdline: $c, probe: $p}')"
	mem
	case "$p" in
		P2 | P4) ;;             # the session side finishes these
		P3)
			wait_for "$WAIT_S" systemctl is-active --quiet plymouth-quit-wait.service || true
			journals
			"$EMIT" "done" "$p"
			;;
		P1 | P4g)
			if wait_for "$WAIT_S" pgrep -x sddm-greeter-qt6; then
				theme=$(sed -n 's/^Current=//p' "$SDDM_CONF_DIR"/*.conf 2> /dev/null | tail -n1)
				"$EMIT" frame el.greeter "$(jq -cn --argjson pid "$(pgrep -x sddm-greeter-qt6 | head -n1)" \
					--arg th "${theme:-unknown}" '{pid: $pid, theme: $th}')"
			fi
			[ "$p" = P4g ] && analyze
			[ "$p" = P1 ] && journals
			"$EMIT" "done" "$p"
			;;
		*) "$EMIT" "done" "$p" ;;
	esac
}

session() {
	p=$(probe)
	"$EMIT" frame el.session "$(jq -cn --argjson u "$(id -u)" --arg s "${XDG_SESSION_TYPE:-unknown}" \
		'{uid: $u, session_type: $s}')"
	capped=false
	if wait_for "$SETTLE_CAP_S" pgrep -x plasmashell; then
		sleep "$SETTLE_S"
	else
		capped=true
	fi
	mem
	"$EMIT" frame el.settled "$(jq -cn --argjson c "$capped" '{capped: $c}')"
	case "$p" in
		P2)
			journals
			f=$(blob appletsrc cat "$APPLETSRC")
			"$EMIT" frame el.file "$(jq -cn --arg f "$f" '{appletsrc: $f}')"
			;;
		P4)
			wait_for "$WAIT_S" systemd-analyze time || true
			analyze
			;;
	esac
	mem
	"$EMIT" "done" "$p"
}

case "${1-}" in
	system) system ;;
	session) session ;;
	*)
		echo "usage: el-reporter system | session" >&2
		exit 2
		;;
esac
