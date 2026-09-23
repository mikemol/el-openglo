package el.root_helpers_test

import data.el.root_helpers as rh
import rego.v1

theme := "/usr/share/plymouth/themes/el-openglo-EL-Openglo/el-openglo-EL-Openglo.plymouth"

layout := {"kind": "layout", "variant": "EL-Openglo", "dir": "el-openglo-EL-Openglo",
	"plymouth_files": ["el-openglo-EL-Openglo.plymouth"],
	"refs": {"el-openglo-EL-Openglo.plymouth": {"script_file": "/x.script", "script_exists": true, "image_dir": "/x", "image_dir_exists": true}}}

ply(scenario, exit, extra) := object.union({"kind": "run", "helper": "el-openglo-plymouth", "scenario": scenario,
	"exit": exit, "stdout": "", "stderr": "", "tool_log": [], "alternative": null, "dropin": null,
	"sddm_conf_written": false, "want_theme": theme, "want_name": "el-openglo-EL-Openglo"}, extra)

sddm(scenario, exit, current) := {"kind": "run", "helper": "el-openglo-sddm", "scenario": scenario, "exit": exit,
	"stdout": "", "stderr": "", "tool_log": [], "alternative": null,
	"dropin": {"text": sprintf("[Theme]\nCurrent=%s\n", [current])}, "sddm_conf_written": false,
	"want_current": "el-openglo-azure-lit", "want_theme_dir_exists": true}

good := [
	layout,
	ply("happy", 0, {"alternative": {"link": theme}, "tool_log": ["update-alternatives --set", "update-initramfs -u"]}),
	ply("alternatives_fail", 1, {}),
	ply("no_update_initramfs", 1, {"stderr": "update-initramfs not found"}),
	ply("no_initramfs_flag", 0, {"stdout": "SKIP: initramfs rebuild"}),
	ply("set_default_theme_route", 0, {"tool_log": ["plymouth-set-default-theme -R el-openglo-EL-Openglo"]}),
	ply("no_route", 1, {"stderr": "neither update-alternatives nor plymouth-set-default-theme"}),
	sddm("theme", 0, "el-openglo-azure-lit"),
	sddm("unknown_variant", 1, "x"),
	sddm("breeze_after_theme", 0, "breeze"),
]

swap(scenario, c) := array.concat([x | some x in good; object.get(x, "scenario", "") != scenario], [c])

test_admits_a_good_tree if {
	count(rh.deny) == 0 with input as {"cases": good}
}

test_h0_refuses_an_absent_population if {
	"H0: no case was measured" in rh.deny with input as {}
}

test_g2_refuses_a_debian_only_layout if {
	bad := object.union(layout, {"plymouth_files": ["el-openglo.plymouth"]})
	some msg in rh.deny with input as {"cases": array.concat([x | some x in good; x.kind != "layout"], [bad])}
	startswith(msg, "G2: el-openglo-EL-Openglo holds")
}

test_g2_refuses_a_dangling_scriptfile if {
	bad := object.union(layout, {"refs": {"el-openglo-EL-Openglo.plymouth": {"script_file": "/y", "script_exists": false, "image_dir": "/x", "image_dir_exists": true}}})
	some msg in rh.deny with input as {"cases": array.concat([x | some x in good; x.kind != "layout"], [bad])}
	contains(msg, "ScriptFile /y does not resolve")
}

test_g3_refuses_a_swallowed_alternatives_failure if {
	some msg in rh.deny with input as {"cases": swap("alternatives_fail", ply("alternatives_fail", 0, {}))}
	startswith(msg, "G3: el-openglo-plymouth/alternatives_fail exited 0")
}

test_g3_refuses_a_silent_initramfs_skip if {
	some msg in rh.deny with input as {"cases": swap("no_update_initramfs", ply("no_update_initramfs", 0, {}))}
	startswith(msg, "G3: el-openglo-plymouth/no_update_initramfs exited 0")
}

test_g3_refuses_a_failure_that_names_nothing if {
	some msg in rh.deny with input as {"cases": swap("no_update_initramfs", ply("no_update_initramfs", 1, {"stderr": "oops"}))}
	contains(msg, "without naming update-initramfs")
}

test_g3_refuses_an_unprinted_skip if {
	some msg in rh.deny with input as {"cases": swap("no_initramfs_flag", ply("no_initramfs_flag", 0, {}))}
	startswith(msg, "G3: el-openglo-plymouth/no_initramfs_flag")
}

test_g3_refuses_the_wrong_alternative if {
	c := ply("happy", 0, {"alternative": {"link": "/usr/share/plymouth/themes/el-openglo-EL-Openglo/el-openglo.plymouth"}, "tool_log": ["update-initramfs -u"]})
	some msg in rh.deny with input as {"cases": swap("happy", c)}
	contains(msg, "left default.plymouth at")
}

test_g1_refuses_the_breeze_background_route if {
	some msg in rh.deny with input as {"cases": swap("theme", sddm("theme", 0, "breeze"))}
	startswith(msg, "G1: el-openglo-sddm/theme did not select el-openglo-azure-lit")
}

test_g1_refuses_no_way_back if {
	some msg in rh.deny with input as {"cases": swap("breeze_after_theme", sddm("breeze_after_theme", 0, "el-openglo-openglo"))}
	startswith(msg, "G1: el-openglo-sddm/breeze_after_theme")
}

test_g1_refuses_an_sddm_conf_write if {
	c := object.union(sddm("theme", 0, "el-openglo-azure-lit"), {"sddm_conf_written": true})
	some msg in rh.deny with input as {"cases": swap("theme", c)}
	contains(msg, "wrote sddm.conf")
}

test_a_seamless_helper_is_withheld if {
	w := {"kind": "run", "helper": "el-openglo-sddm", "scenario": "theme", "withheld": "no seam"}
	some msg in rh.withheld with input as {"cases": [layout, w]}
	contains(msg, "no seam")
}
