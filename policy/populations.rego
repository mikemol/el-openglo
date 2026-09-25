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

deny contains msg if {
	count(object.get(input, "files", [])) == 0
	msg := "P0: no file was in the census scope"
}

# ⚑ EXACTLY ONCE: every site carries borrowed / recursive / marked (booleans) and
# reach (a string). One of those null or absent is a could-not-say: the site is
# WITHHELD by name and judged by no rule (`not c.borrowed` read null as borrowed).
# `reason` is legitimately null on an unmarked site and is not required.
site_fields := ["borrowed", "recursive", "marked"]

measured(c) if {
	every f in site_fields { is_boolean(object.get(c, f, null)) }
	is_string(object.get(c, "reach", null))
}

withheld contains msg if {
	some c in object.get(input, "cases", [])
	some f in site_fields
	not is_boolean(object.get(c, f, null))
	msg := sprintf("P1: %v:%v: %s was not measured", [object.get(c, "module", null), object.get(c, "line", null), f])
}

withheld contains msg if {
	some c in object.get(input, "cases", [])
	not is_string(object.get(c, "reach", null))
	msg := sprintf("P1: %v:%v: reach was not measured", [object.get(c, "module", null), object.get(c, "line", null)])
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
	measured(c)
	c.borrowed == false
	c.kind != "git-ls-files"
	c.recursive == true
	c.reach in {"root", "unknown"}
	c.marked == false
	msg := sprintf("P1: %s:%d %s(%s) walks from %s reach with no `# population:` reason; read the population from scripts/git_tracked.py", [c.module, c.line, c.kind, c.root, c.reach])
}

# METADATA
# title: "P3 — a raw `git ls-files` outside the authority"
# description: |
#   2026-09-25 (R6): check_license read its population with a raw `git ls-files`,
#   bypassing scripts/git_tracked.py, and died with git's exit 128 in paperkit's Δ
#   sandbox (a copy with no .git) — graded `broken` there. git_tracked answers from
#   git where there is one and from a bounded walk where there is not. Only it may
#   run `git ls-files`; anything else carries a `# population:` reason or calls it.
deny contains msg if {
	some c in object.get(input, "cases", [])
	measured(c)
	c.borrowed == false
	c.kind == "git-ls-files"
	c.module != "scripts/git_tracked.py"
	c.marked == false
	msg := sprintf("P3: %s:%d runs `git ls-files` directly, bypassing scripts/git_tracked.py (which works where there is no .git — the Δ sandbox); call git_tracked.files()", [c.module, c.line])
}

deny contains msg if {
	some c in object.get(input, "cases", [])
	measured(c)
	c.borrowed == false
	c.marked == true
	trim_space(object.get(c, "reason", "")) == ""
	msg := sprintf("P2: %s:%d is marked `# population:` with no reason", [c.module, c.line])
}

# A borrowed file (a symlink into ../substrate) is substrate's to fix: measured,
# reported, never denied here.
withheld contains msg if {
	some c in object.get(input, "cases", [])
	measured(c)
	c.borrowed == true
	c.recursive == true
	c.reach in {"root", "unknown"}
	c.marked == false
	msg := sprintf("P1: %s:%d %s(%s) — a SUBSTRATE finding (borrowed file)", [c.module, c.line, c.kind, c.root])
}

withheld contains msg if {
	some u in object.get(input, "unreadable", [])
	msg := sprintf("P0: %s withheld: %s", [u.module, u.withheld])
}

admitted contains f if {
	some f in object.get(input, "files", [])
}
