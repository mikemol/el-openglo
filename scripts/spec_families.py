#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""spec_families.py — which closure family does each policy spec belong to? (W661, under W660)

The closure tree is nested (closures/<kind>/<family>/<spec>.bzl), so a port edits only its family. A family
is chosen by WHAT THE SPEC MEASURES, so the surface's owner edits one family:

    palette   colour law and contrast (the palette, its roles, legibility, separation)
    targets   one emitted surface, font or asset (a terminal, a browser, the clock, the cursors)
    display   segment geometry, the configuration pages and the render-time values
    gate      the repo's own machinery (the gate, the closure, the build, the queue, the licence)

    scripts/spec_families.py            # every spec and its family, one per line
    scripts/spec_families.py --json     # the population, the assignment, and what is unassigned or unknown
    scripts/spec_families.py --tags     # the family each rego carries in its METADATA (custom.family)
    scripts/spec_families.py --apply    # write the table's family into every untagged rego, once
    scripts/spec_families.py --selftest

This table is the SEED: --apply writes the family once into each spec's rego METADATA (`custom.family`,
on the block that directly precedes `package`), which is authoritative from then on; the family names are
a repo-level call and may be renamed. --apply refuses a file that already carries a family.

⚑ WEAKNESS, STATED. The assignment is a judgement made by name and by reading each spec's header, not a
measurement of the code; it proves every spec has exactly one family, not that the family is the best one.
--tags reads the line `#   family: NAME` inside the block above `package`, not the parsed annotation.
"""

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

FAMILIES = {
    "palette": (
        "codomain legibility monet notify_roles palette_chain palette_graph rehue relations "
        "role_theme selection_contrast separation states symmetry token_source tokens union "
        "urgency_cues use_of_colour"
    ),
    "targets": (
        "android_clock aperture chrome chrome_zips css cursors firefox font font_compiler "
        "ghost_balance ghost_composite glb gtk kerning lnf marquee_body marquee_live metrics "
        "netlist_render nodal plasma_air plymouth_digits screens sddm taskswitch terminals "
        "vscode windows"
    ),
    "display": (
        "config_load config_page config_reach display_registry geometry_source projection "
        "render_constants serial"
    ),
    "gate": (
        "action_key atomic_writes bazel_build census closure compiles consumers contracts deb deps "
        "ebuild embedded_markup emitters_run gcalc_api guest_recipe hooks inherit license log_content "
        "qt_sandbox mark migration package_imports package_load partial plugin_ids "
        "populations post_commit publishing qml_lint readme rego_lint root_helpers routes "
        "runtime_warnings scope_recorded solver_roots st_api standards template_parity tree_writes"
    ),
}

FAMILY_KEY = "#   family: "


def assignment():
    """{spec: [family, ...]}: every family a spec is listed under (one is the requirement)."""
    out = {}
    for family, names in FAMILIES.items():
        for spec in names.split():
            out.setdefault(spec, []).append(family)
    return out


def specs(root=ROOT):
    """The policy specs in the tree: every tracked policy/NAME.rego that is not a test."""
    import git_tracked

    return sorted(
        os.path.basename(p)[: -len(".rego")]
        for p in git_tracked.files("policy/*.rego", root=root)
        if not p.endswith("_test.rego") and os.path.dirname(p) == "policy"
    )


def _block(lines):
    """(package line index, first index of the comment run directly above it), or (None, None)."""
    pkg = next((i for i, ln in enumerate(lines) if ln.startswith("package ")), None)
    if pkg is None:
        return None, None
    start = pkg
    while start > 0 and lines[start - 1].startswith("#"):
        start -= 1
    return pkg, start


def tag_of(text):
    """The family a rego's package-level METADATA carries, or None."""
    lines = text.splitlines()
    pkg, start = _block(lines)
    if pkg is None:
        return None
    for ln in lines[start:pkg]:
        if ln.startswith(FAMILY_KEY):
            return ln[len(FAMILY_KEY) :].strip()
    return None


def tagged(text, family):
    """(new text, why): `text` with `custom.family` added to the block above `package`; why is empty on
    success, or the reason the file was left alone."""
    lines = text.splitlines()
    pkg, start = _block(lines)
    if pkg is None:
        return text, "no package line"
    if tag_of(text) is not None:
        return text, "already carries a family"
    block = lines[start:pkg]
    if any(ln.startswith("# custom:") for ln in block):
        return text, "already has a custom: key"
    add = ["# custom:", f"{FAMILY_KEY}{family}"]
    if "# METADATA" in block:
        lines[pkg:pkg] = add
    else:
        lines[pkg:pkg] = ["# METADATA", *add]
    return "\n".join(lines) + "\n", ""


def measure(population=None, table=None, tags=None):
    """The facts: the population, the families each spec is listed under, the defects, and the tags."""
    population = specs() if population is None else population
    table = assignment() if table is None else table
    tags = {} if tags is None else tags
    return {
        "specs": len(population),
        "unassigned": sorted(s for s in population if s not in table),
        "unknown": sorted(s for s in table if s not in population),
        "ambiguous": sorted(s for s, f in table.items() if len(f) > 1),
        "untagged": sorted(s for s in population if tags.get(s) is None),
        "mismatched": sorted(
            s for s in population if tags.get(s) not in (None, *table.get(s, []))
        ),
        "families": {
            f: sorted(n for n in population if table.get(n) == [f]) for f in FAMILIES
        },
    }


def read_tags(population, root=ROOT):
    out = {}
    for spec in population:
        with open(os.path.join(root, "policy", f"{spec}.rego"), encoding="utf-8") as fh:
            out[spec] = tag_of(fh.read())
    return out


def apply(population, table, root=ROOT):
    """Tag every untagged rego with its table family; (done, skipped {spec: why})."""
    done, skipped = [], {}
    for spec in population:
        family = table.get(spec, [None])[0]
        path = os.path.join(root, "policy", f"{spec}.rego")
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        if family is None:
            skipped[spec] = "no family in the table"
            continue
        new, why = tagged(text, family)
        if why:
            skipped[spec] = why
            continue
        tmp = f"{path}.tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(new)
        os.replace(tmp, path)
        done.append(spec)
    return done, skipped


def main(argv):
    args = argv[1:]
    if args not in ([], ["--json"], ["--tags"], ["--apply"]):
        print(f"spec_families: unknown arguments {args!r}", file=sys.stderr)
        return 2
    population = specs()
    if not population:
        print(
            "spec_families: no policy spec was found; the search is broken",
            file=sys.stderr,
        )
        return 2
    table = assignment()
    if args == ["--apply"]:
        done, skipped = apply(population, table)
        for spec, why in sorted(skipped.items()):
            print(f"spec_families: skipped {spec}: {why}", file=sys.stderr)
        print(
            f"spec_families: tagged {len(done)} of {len(population)} spec(s); {len(skipped)} skipped"
        )
        return 0 if done or not skipped else 1
    facts = measure(population, table, read_tags(population))
    if args == ["--json"]:
        print(json.dumps(facts, indent=1))
        return 0
    for spec in population:
        print(f"{spec}\t{'+'.join(table.get(spec, ['?']))}")
    bad = len(facts["unassigned"]) + len(facts["unknown"]) + len(facts["ambiguous"])
    if args == ["--tags"]:
        bad += len(facts["mismatched"])
        print(
            f"spec_families: {len(population) - len(facts['untagged'])} of {len(population)} spec(s) tagged; "
            f"{len(facts['untagged'])} untagged, {len(facts['mismatched'])} mismatched",
            file=sys.stderr,
        )
    return 1 if bad else 0


def _selftest():
    ok = True

    def chk(label, got, want):
        nonlocal ok
        print(
            f"  {'ok  ' if got == want else 'FAIL'} {label}"
            + ("" if got == want else f": got {got!r} want {want!r}")
        )
        ok = ok and got == want

    table = {"a": ["gate"], "b": ["gate", "palette"], "z": ["gate"]}
    m = measure(["a", "b", "c"], table, {"a": "gate", "b": None, "c": "palette"})
    chk("a spec with no family is unassigned", m["unassigned"], ["c"])
    chk("a listed name that is no spec is unknown", m["unknown"], ["z"])
    chk("a spec under two families is ambiguous", m["ambiguous"], ["b"])
    chk("a spec with no tag is untagged", m["untagged"], ["b"])
    chk("a tag outside the table's families is mismatched", m["mismatched"], ["c"])
    chk(
        "a clean population has no defect",
        [
            measure(["a"], {"a": ["gate"]}, {"a": "gate"})[k]
            for k in ("unassigned", "unknown", "ambiguous", "untagged", "mismatched")
        ],
        [[], [], [], [], []],
    )
    with_block = "# METADATA\n# title: x\n# description: |\n#   y\npackage el.x\n\nimport rego.v1\n"
    new, why = tagged(with_block, "gate")
    chk(
        "a METADATA block gains the custom key before package",
        (why, tag_of(new)),
        ("", "gate"),
    )
    chk(
        "the block keeps its title and ends directly above package",
        new.splitlines()[3:7],
        ["#   y", "# custom:", "#   family: gate", "package el.x"],
    )
    bare = "package el.x\n\nimport rego.v1\n"
    new, why = tagged(bare, "display")
    chk(
        "a package with no block gains one",
        (why, tag_of(new), new.splitlines()[0]),
        ("", "display", "# METADATA"),
    )
    chk(
        "a tagged file is refused, not retagged",
        tagged(new, "gate")[1],
        "already carries a family",
    )
    chk(
        "a file with no package is left alone",
        tagged("x := 1\n", "gate"),
        ("x := 1\n", "no package line"),
    )
    chk(
        "a plain comment above the block is not the block",
        tag_of("# family note\n#   family: gate\n\npackage el.x\n"),
        None,
    )
    live = measure(population=specs(), tags=read_tags(specs()))
    chk(
        "the live tree has specs to judge (n of m, never 0 of 0)",
        live["specs"] > 0,
        True,
    )
    chk(
        "every live spec has exactly one family",
        (live["unassigned"], live["unknown"], live["ambiguous"]),
        ([], [], []),
    )
    print("spec_families selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    os.chdir(ROOT)
    if sys.argv[1:] == ["--selftest"]:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
