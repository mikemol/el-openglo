# METADATA
# title: "P0 — a census that read no file measured nothing"
# description: |
#   The measurement is `scripts/check_populations.py --json`: every disk
#   enumeration (os.walk, rglob, recursive glob, listdir, scandir) in the tracked
#   scripts/*.py, catalog/library/*.py and top-level *.py, with the static REACH
#   of its root argument. An empty file population is a broken search, not a
#   clean tree. (Zero SITES over a non-empty population is admissible: a tree
#   with no disk walk at all is the goal, not a defect.)
package el.populations

import rego.v1

import data.el.truth

deny contains msg if {
	count(object.get(input, "files", [])) == 0
	msg := "P0: no file was in the census scope"
}

# METADATA
# title: "P1 — no unmarked recursive walk that can reach the repo root"
# description: |
#   2026-09-22 (build_graph) and 2026-09-23 (check_compiles): an os.walk of ROOT
#   descended into .claude/worktrees/, .build/, .tree-writes/, .ebuild-witness/
#   and counted files that are not this tree. A population over the tree comes
#   from scripts/git_tracked.py (git ls-files) or a declared roster. A recursive
#   walk whose root is the repo root — or cannot be shown bounded (`unknown`) —
#   must carry `# population: <reason>` stating its bound.
deny contains msg if {
	some c in object.get(input, "cases", [])
	not c.borrowed
	truth.py(c.recursive)
	c.reach in {"root", "unknown"}
	not c.marked
	msg := sprintf("P1: %s:%d %s(%s) walks from %s reach with no `# population:` reason; read the population from scripts/git_tracked.py", [c.module, c.line, c.kind, c.root, c.reach])
}

deny contains msg if {
	some c in object.get(input, "cases", [])
	not c.borrowed
	truth.py(c.marked)
	trim_space(object.get(c, "reason", "")) == ""
	msg := sprintf("P2: %s:%d is marked `# population:` with no reason", [c.module, c.line])
}

# A borrowed file (a symlink into ../substrate) is substrate's to fix: measured,
# reported, never denied here.
withheld contains msg if {
	some c in object.get(input, "cases", [])
	truth.py(c.borrowed)
	truth.py(c.recursive)
	c.reach in {"root", "unknown"}
	not c.marked
	msg := sprintf("P1: %s:%d %s(%s) — a SUBSTRATE finding (borrowed file)", [c.module, c.line, c.kind, c.root])
}

withheld contains msg if {
	some u in object.get(input, "unreadable", [])
	msg := sprintf("P0: %s withheld: %s", [u.module, u.withheld])
}

admitted contains f if {
	some f in object.get(input, "files", [])
}
