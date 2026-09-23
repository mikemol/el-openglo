#!/bin/sh
# el-serial-emit — the GUEST writer of el-serial/1 (catalog/guest-image.md (f)).
# POSIX sh + jq + coreutils (base64, fold, sha256sum, wc) + util-linux flock.
# There is no Python in the guest.
#
#   el-serial-emit frame KIND 'PAYLOAD-JSON'   one record; the envelope (boot, t) is added here
#   el-serial-emit blob LABEL FILE             blob.part 0..of-1 + blob.end; prints the blob id
#   el-serial-emit done PROBE                  el.done with records = its own SEQ
#
# Every kind, payload key and type comes from the spec JSON that
# scripts/el_serial_emit.py and scripts/read_serial.py also load; this file
# names no kind except the three frames it builds itself (blob.part, blob.end,
# el.done), and even those are validated against the table. `type_ok` below
# mirrors scripts/el_serial_spec.py:type_ok arm for arm.
#
# Weakness: this file is only syntax-checked on the host (`sh -n`); jq is not
# run there. The Python reference writer is what the round trip proves. The
# first guest boot (W71e) is where these bytes meet read_serial.py.
set -eu

SPEC=${EL_SERIAL_SPEC:-/usr/share/el-openglo/el-serial-spec.json}
DEV=${EL_SERIAL_DEV:-/dev/ttyS0}
RUN=${EL_SERIAL_RUN:-/run}

usage() {
	echo "usage: el-serial-emit frame KIND PAYLOAD-JSON | blob LABEL FILE | done PROBE" >&2
	exit 2
}

case "${1-}" in
	frame | blob) [ $# -eq 3 ] || usage ;;
	done) [ $# -eq 2 ] || usage ;;
	*) usage ;;
esac

TYPE_OK='
def type_ok($s; $t):
  if $t == "str" then type == "string"
  elif $t == "int" then type == "number" and . == floor and . >= 0
  elif $t == "bool" then type == "boolean"
  elif $t == "object" then type == "object"
  elif $t == "blob" or $t == "blob_id" then type == "string" and test("^b(0|[1-9][0-9]*)$")
  elif $t == "b64" then type == "string" and length <= $s.part_b64_chars and test("^[A-Za-z0-9+/=]*$")
  elif $t == "sha256" then type == "string" and test("^[0-9a-f]{64}$")
  elif $t == "boot_id" then type == "string" and test("^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
  else error("el-serial spec names unknown type \($t)") end;
'

MARKER=$(jq -r .marker "$SPEC")
MAXLINE=$(jq -r .max_line_bytes "$SPEC")
PARTW=$(jq -r .part_b64_chars "$SPEC")
read -r BOOT < /proc/sys/kernel/random/boot_id

# One lock hold per invocation: a blob's parts and its end are consecutive SEQs.
exec 9> "$RUN/el-serial.lock"
flock 9
SEQ=0
[ -f "$RUN/el-serial.seq" ] && read -r SEQ < "$RUN/el-serial.seq"

now_cs() {
	read -r up _ < /proc/uptime
	echo $(( ${up%.*} * 100 + 1${up#*.} - 100 ))
}

# emit KIND PAYLOAD: validate against the spec, write one line, advance SEQ.
emit() {
	json=$(jq -cSa -n --arg kind "$1" --argjson p "$2" --arg boot "$BOOT" \
		--argjson t "$(now_cs)" --slurpfile spec "$SPEC" "$TYPE_OK"'
	  $spec[0] as $s
	  | if ($p | type) != "object" or ($p | has("boot") or has("t"))
	      then error("\($kind): payload must be an object without boot/t") else . end
	  | ($s.envelope + ($s.kinds[$kind] // error("unknown kind \($kind)"))) as $want
	  | ($p + {boot: $boot, t: $t}) as $o
	  | if ($o | keys) != ($want | keys)
	      then error("\($kind): keys \($o | keys) are not exactly \($want | keys)") else . end
	  | [$want | to_entries[] | .key as $k | select(($o[$k] | type_ok($s; .value)) | not) | $k] as $bad
	  | if ($bad | length) > 0 then error("\($kind): wrong type for \($bad)") else $o end')
	line="$MARKER $SEQ $1 $json"
	n=$(printf '%s' "$line" | wc -c)
	if [ "$n" -gt "$MAXLINE" ]; then
		echo "el-serial-emit: $1: $n bytes > $MAXLINE; send it as a blob" >&2
		exit 1
	fi
	printf '%s\n' "$line" >> "$DEV"
	SEQ=$((SEQ + 1))
	echo "$SEQ" > "$RUN/el-serial.seq"
}

case "$1" in
	frame)
		emit "$2" "$3"
		;;
	done)
		emit el.done "$(jq -cn --arg probe "$2" --argjson records "$SEQ" '{probe: $probe, records: $records}')"
		;;
	blob)
		tmp=$(mktemp)
		trap 'rm -f "$tmp"' EXIT
		# ONE base64 stream of the whole file, cut into PARTW-char parts; the
		# trailing echo terminates fold's last line, and makes an empty file ONE empty part
		base64 -w0 < "$3" | fold -w "$PARTW" > "$tmp"
		echo >> "$tmp"
		of=$(($(wc -l < "$tmp") + 0))
		id="b$SEQ"
		n=0
		while IFS= read -r chunk; do
			emit blob.part "$(jq -cn --arg id "$id" --argjson n "$n" --argjson of "$of" --arg b64 "$chunk" \
				'{id: $id, n: $n, of: $of, b64: $b64}')"
			n=$((n + 1))
		done < "$tmp"
		sha=$(sha256sum < "$3")
		emit blob.end "$(jq -cn --arg id "$id" --arg sha "${sha%% *}" --argjson bytes "$(($(wc -c < "$3") + 0))" \
			--argjson of "$of" --arg label "$2" '{id: $id, sha256: $sha, bytes: $bytes, of: $of, label: $label}')"
		echo "$id"
		;;
esac
