# METADATA
# title: "H0 — no measured case admits nothing"
# description: |
#   The measurement is `scripts/check_root_helpers.py --json`: the plymouth theme
#   layout per variant, and each root helper run against a scratch root with a
#   stubbed PATH. An empty population is a broken search, not a clean tree.
package el.root_helpers

import rego.v1

import data.el.truth

#   ⚑ EVERY CASE LANDS IN EXACTLY ONE OF withheld / deny / admitted. A fact
#   check_root_helpers.py ALWAYS emits that is null or absent could not be said:
#   H2 withholds it and no rule judges that case. `alternative`, `dropin` and
#   `want_current` are legitimately null (no file written; --breeze / an unknown
#   variant), so they are not in the lists.

# a withholding REASON: null / "" / absent is "not withheld"
held(c) if truth.py(object.get(c, "withheld", null))

missing(obj, fields) := {f | some f in fields; object.get(obj, f, null) == null}

run_fields := ["exit", "stdout", "stderr", "tool_log", "sddm_conf_written"]

helper_fields := {
	"el-openglo-plymouth": ["want_theme", "want_name"],
	"el-openglo-sddm": ["want_theme_dir_exists"],
}

run_missing(c) := missing(c, array.concat(run_fields, object.get(helper_fields, c.helper, [])))

ref_fields := ["script_file", "script_exists", "image_dir", "image_dir_exists"]

layout_missing(c) := m if {
	top := missing(c, ["dir", "plymouth_files", "refs"])
	refs := {sprintf("%s.%s", [f, x]) | some f, r in object.get(c, "refs", {}); some x in missing(r, ref_fields)}
	m := top | refs
}

runs := [c |
	some c in object.get(input, "cases", [])
	c.kind == "run"
	not held(c)
	count(run_missing(c)) == 0
]

layouts := [c |
	some c in object.get(input, "cases", [])
	c.kind == "layout"
	count(layout_missing(c)) == 0
]

# METADATA
# title: "H2 — a fact the measurement did not state is withheld, not judged"
withheld contains msg if {
	some c in object.get(input, "cases", [])
	c.kind == "run"
	not held(c)
	some f in run_missing(c)
	msg := sprintf("H2: %s/%s: %s was not measured", [c.helper, c.scenario, f])
}

withheld contains msg if {
	some i, c in object.get(input, "cases", [])
	object.get(c, "kind", null) == null
	msg := sprintf("H2: case %d: kind was not measured", [i])
}

withheld contains msg if {
	some c in object.get(input, "cases", [])
	c.kind == "layout"
	some f in layout_missing(c)
	msg := sprintf("H2: layout %v: %s was not measured", [object.get(c, "dir", object.get(c, "variant", null)), f])
}

deny contains msg if {
	count(object.get(input, "cases", [])) == 0
	msg := "H0: no case was measured"
}

# METADATA
# title: "H1 — make_deb's own VARIANTS is the roster (make_schemes.GRID)"
# description: |
#   The layouts are measured over the ROSTER; a package whose VARIANTS drops a
#   variant would ship no theme for it — a deny, not a shorter layout list (W61 R1).
deny contains msg if {
	some d in object.get(input, "roster_drift", [])
	msg := sprintf("H1: %s %s", [d.variant, d.why])
}

withheld contains msg if {
	some c in object.get(input, "cases", [])
	truth.py(c.withheld)
	msg := sprintf("H0: %s/%s withheld: %s", [c.helper, c.scenario, c.withheld])
}

# a case is judged when it ran, or is a layout
admitted contains sprintf("%s/%s", [c.helper, c.scenario]) if {
	some c in runs
	not deny_of(c)
}

admitted contains c.dir if {
	some c in layouts
	not layout_bad(c)
}

deny_of(c) := true if {
	some msg in deny
	contains(msg, sprintf("%s/%s", [c.helper, c.scenario]))
}

# METADATA
# title: "G2 — the theme directory and its .plymouth file agree"
# description: |
#   plymouth-set-default-theme (Fedora, Arch, Gentoo) selects <name> by reading
#   <name>/<name>.plymouth; a dir el-openglo-X holding el-openglo.plymouth is
#   selectable only through Debian alternatives. And the config's ScriptFile and
#   ImageDir must resolve inside the installed tree.
layout_bad(c) := true if {
	not sprintf("%s.plymouth", [c.dir]) in c.plymouth_files
}

layout_bad(c) := true if {
	some f, r in c.refs
	r.script_exists == false
}

layout_bad(c) := true if {
	some f, r in c.refs
	r.image_dir_exists == false
}

deny contains msg if {
	count(object.get(input, "cases", [])) > 0
	# the RAW layout population: an unmeasured layout is withheld (H2), not absent
	count([c | some c in input.cases; c.kind == "layout"]) == 0
	msg := "G2: no plymouth layout was measured"
}

deny contains msg if {
	some c in layouts
	not sprintf("%s.plymouth", [c.dir]) in c.plymouth_files
	msg := sprintf("G2: %s holds %v, not %s.plymouth", [c.dir, c.plymouth_files, c.dir])
}

deny contains msg if {
	some c in layouts
	some f, r in c.refs
	r.script_exists == false
	msg := sprintf("G2: %s/%s ScriptFile %s does not resolve", [c.dir, f, r.script_file])
}

deny contains msg if {
	some c in layouts
	some f, r in c.refs
	r.image_dir_exists == false
	msg := sprintf("G2: %s/%s ImageDir %s does not resolve", [c.dir, f, r.image_dir])
}

run(helper, scenario) := c if {
	some c in runs
	c.helper == helper
	c.scenario == scenario
}

# METADATA
# title: "G3 — the plymouth helper selects, or fails LOUDLY"
# description: |
#   Happy path: exit 0, default.plymouth points at <name>/<name>.plymouth, the
#   initramfs is rebuilt. A failing update-alternatives, a missing
#   update-initramfs, or no selection route at all is a non-zero exit whose
#   message names the tool. Skipping the rebuild is allowed only when asked
#   (--no-initramfs) and is printed as a SKIP.
deny contains msg if {
	c := run("el-openglo-plymouth", "happy")
	c.exit != 0
	msg := sprintf("G3: el-openglo-plymouth/happy exited %v: %s", [c.exit, c.stderr])
}

deny contains msg if {
	c := run("el-openglo-plymouth", "happy")
	object.get(c, ["alternative", "link"], null) != c.want_theme
	msg := sprintf("G3: el-openglo-plymouth/happy left default.plymouth at %v, not %s", [c.alternative, c.want_theme])
}

deny contains msg if {
	c := run("el-openglo-plymouth", "happy")
	not "update-initramfs -u" in c.tool_log
	msg := "G3: el-openglo-plymouth/happy did not rebuild the initramfs"
}

deny contains msg if {
	c := run("el-openglo-plymouth", "alternatives_fail")
	c.exit == 0
	msg := "G3: el-openglo-plymouth/alternatives_fail exited 0 though update-alternatives failed"
}

deny contains msg if {
	c := run("el-openglo-plymouth", "no_update_initramfs")
	c.exit == 0
	msg := "G3: el-openglo-plymouth/no_update_initramfs exited 0 with no update-initramfs"
}

deny contains msg if {
	c := run("el-openglo-plymouth", "no_update_initramfs")
	c.exit != 0
	not contains(c.stderr, "update-initramfs")
	msg := "G3: el-openglo-plymouth/no_update_initramfs failed without naming update-initramfs"
}

deny contains msg if {
	c := run("el-openglo-plymouth", "no_initramfs_flag")
	not skip_printed(c)
	msg := sprintf("G3: el-openglo-plymouth/no_initramfs_flag did not exit 0 with a printed SKIP (exit %v)", [c.exit])
}

skip_printed(c) if {
	c.exit == 0
	contains(c.stdout, "SKIP")
}

deny contains msg if {
	c := run("el-openglo-plymouth", "set_default_theme_route")
	not sprintf("plymouth-set-default-theme -R %s", [c.want_name]) in c.tool_log
	msg := sprintf("G3: el-openglo-plymouth/set_default_theme_route did not run plymouth-set-default-theme -R %s (exit %v)", [c.want_name, c.exit])
}

deny contains msg if {
	c := run("el-openglo-plymouth", "no_route")
	not loud_no_route(c)
	msg := "G3: el-openglo-plymouth/no_route did not fail naming both selection tools"
}

loud_no_route(c) if {
	c.exit != 0
	contains(c.stderr, "update-alternatives")
	contains(c.stderr, "plymouth-set-default-theme")
}

# METADATA
# title: "G1 — the SDDM helper selects the W66 greeter, reversibly"
# description: |
#   `el-openglo-sddm VARIANT` writes the drop-in /etc/sddm.conf.d/el-openglo.conf
#   with [Theme] Current=el-openglo-<slug>, a theme that is installed; it never
#   writes sddm.conf. `--breeze` is the way back: Current=breeze. An unknown
#   variant is refused.
deny contains msg if {
	c := run("el-openglo-sddm", "theme")
	not selects(c, c.want_current)
	msg := sprintf("G1: el-openglo-sddm/theme did not select %v (exit %v, drop-in %v)", [c.want_current, c.exit, c.dropin])
}

deny contains msg if {
	c := run("el-openglo-sddm", "theme")
	c.want_theme_dir_exists == false
	msg := sprintf("G1: el-openglo-sddm/theme: %v is not an installed greeter theme", [c.want_current])
}

deny contains msg if {
	some c in runs
	c.helper == "el-openglo-sddm"
	truth.py(c.sddm_conf_written)
	msg := sprintf("G1: el-openglo-sddm/%s wrote sddm.conf; only the drop-in is ours", [c.scenario])
}

deny contains msg if {
	c := run("el-openglo-sddm", "unknown_variant")
	c.exit == 0
	msg := "G1: el-openglo-sddm/unknown_variant exited 0"
}

deny contains msg if {
	c := run("el-openglo-sddm", "breeze_after_theme")
	not selects(c, "breeze")
	msg := sprintf("G1: el-openglo-sddm/breeze_after_theme did not return to Breeze (exit %v, drop-in %v)", [c.exit, c.dropin])
}

selects(c, want) if {
	c.exit == 0
	contains(object.get(c, ["dropin", "text"], ""), sprintf("[Theme]\nCurrent=%s\n", [want]))
}
