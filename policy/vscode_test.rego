package el.vscode_test

import rego.v1

import data.el.vscode

pkg := {"present": true, "parse_error": null, "missing": [], "extra": [], "missing_files": [],
	"wrong_ui": [], "current": true}

vsix := {"opens": true, "corrupt_member": null, "missing": [], "extra": [], "differs": [], "required": []}

good := {"id": "EL-Azure", "present": true, "parse_error": null, "wrong_colours": [], "unmapped_keys": [],
	"wrong_tokens": [], "type": "dark", "want_type": "dark", "current": true,
	"contrast": [{"pair": "editor.foreground on editor.background", "ratio": 9.1, "floor": 4.5}]}

inp(cases) := {"roster": ["EL-Azure"], "cases": cases, "orphans": [], "package": pkg, "vsix": vsix}

test_empty_population_denied if {
	count(vscode.deny) == 1 with input as {}
}

test_complete_admitted if {
	count(vscode.deny) == 0 with input as inp([good])
	count(vscode.admitted) == 1 with input as inp([good])
}

test_declared_but_unmeasured_denied if {
	"V0: EL-Azure: declared but not measured" in vscode.deny with input as object.union(inp([object.union(good, {"id": "Other"})]), {})
}

test_missing_theme_denied if {
	some m in vscode.deny with input as inp([{"id": "EL-Azure", "present": false}])
	startswith(m, "V1: EL-Azure")
}

test_orphan_denied if {
	some m in vscode.deny with input as object.union(inp([good]), {"orphans": ["stray.json"]})
	startswith(m, "V1: orphan theme file stray.json")
}

test_parse_error_denied if {
	i := inp([{"id": "EL-Azure", "present": true, "parse_error": "bad"}])
	some m in vscode.deny with input as i
	startswith(m, "V2: EL-Azure")
	count(vscode.admitted) == 0 with input as i
}

test_wrong_colour_denied if {
	i := inp([object.union(good, {"wrong_colours": [{"key": "editor.background", "role": "view_bg", "got": "#fff", "want": "#000"}]})])
	some m in vscode.deny with input as i
	startswith(m, "V3: EL-Azure: editor.background")
	count(vscode.admitted) == 0 with input as i
}

test_wrong_token_denied if {
	i := inp([object.union(good, {"wrong_tokens": [{"name": "string", "role": "ansi.green", "got": "#1", "want": "#2"}]})])
	some m in vscode.deny with input as i
	startswith(m, "V3: EL-Azure: token string")
}

test_unmapped_key_denied if {
	some m in vscode.deny with input as inp([object.union(good, {"unmapped_keys": ["madeUp.key"]})])
	startswith(m, "V3: EL-Azure: colour key(s) no palette role maps")
}

test_wrong_polarity_denied if {
	some m in vscode.deny with input as inp([object.union(good, {"type": "light"})])
	startswith(m, "V4: EL-Azure")
}

test_low_contrast_denied if {
	i := inp([object.union(good, {"contrast": [{"pair": "editor.foreground on editor.background", "ratio": 2.0, "floor": 4.5}]})])
	"V5: EL-Azure: editor.foreground on editor.background is 2.00:1, below its 4.5:1 floor" in vscode.deny with input as i
	count(vscode.admitted) == 0 with input as i
}

test_unmeasured_pair_withheld_not_denied if {
	i := inp([object.union(good, {"contrast": [{"pair": "p", "ratio": null, "floor": 4.5}]})])
	count(vscode.withheld) == 1 with input as i
	count(vscode.deny) == 0 with input as i
}

test_stale_denied if {
	some m in vscode.deny with input as inp([object.union(good, {"current": false})])
	startswith(m, "V6: EL-Azure")
}

test_package_missing_variant_denied if {
	i := object.union(inp([good]), {"package": object.union(pkg, {"missing": ["EL-Azure"]})})
	"V7: package.json does not contribute EL-Azure" in vscode.deny with input as i
}

test_package_wrong_ui_denied if {
	i := object.union(inp([good]), {"package": object.union(pkg, {"wrong_ui": ["EL-Azure"]})})
	some m in vscode.deny with input as i
	startswith(m, "V7: EL-Azure: uiTheme")
}

test_package_stale_denied if {
	i := object.union(inp([good]), {"package": object.union(pkg, {"current": false})})
	"V7: vscode/package.json is stale; run make_vscode.py" in vscode.deny with input as i
}

test_vsix_unopenable_denied if {
	i := object.union(inp([good]), {"vsix": {"opens": false, "why": "not a zip"}})
	"V8: the packed .vsix does not open: not a zip" in vscode.deny with input as i
}

test_vsix_missing_entry_denied if {
	i := object.union(inp([good]), {"vsix": object.union(vsix, {"required": ["extension.vsixmanifest"]})})
	"V8: the .vsix lacks extension.vsixmanifest" in vscode.deny with input as i
}

test_vsix_differing_entry_denied if {
	i := object.union(inp([good]), {"vsix": object.union(vsix, {"differs": ["extension/package.json"]})})
	"V8: the .vsix entry extension/package.json differs from the folder's emission" in vscode.deny with input as i
}
