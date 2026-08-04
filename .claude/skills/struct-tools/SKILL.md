---
name: struct-tools
description: The artifact → tool routing table for this repo. Read this before reaching for grep/sed/awk over a structured artifact; it names the tool that owns the question. Also the live table the PreToolUse structural-query hook parses.
---

# Structural tools — ask the tool, not the text

**If you have a question the tooling doesn't answer directly, fix the tooling so it
answers your question.** No hand-assembled command lines, no greps, no judgements that
live in a turn instead of a program. A textual query over a structured artifact gets you
a string; the tool gets you the answer.

⚑ **A missing mode is WORK, not a finding.** "No tool covers this, so grep is legitimate
here" is a fact about the METHOD reported as a fact about the SUBSTRATE — the same error
as reading *no match found* as *no such thing exists*. There are no exceptions, only
tools that do not exist yet.

⚑ **THIS TABLE IS READ AT RUN TIME BY THE HOOK.** `scripts/hook_structural_query.py`
parses the rows below to name the owning tool when a textual query hits a structured
artifact. Adding a row teaches the hook with no code change. The hook resolves this file
from the repo root, so it must live HERE — a symlink to another repo's skill routes this
repo's questions to tools that do not exist here, and an ABSENT file makes the hook fire
with no tool named at all (measured, before the hook was adopted).

## artifact → tool

| artifact | tool |
|---|---|
| the retired trademark, anywhere in the tree | `scripts/check_mark.py` — modes: --count, --files |
| whether the generators compile | `scripts/check_compiles.py` — modes: --list |
| third-party imports and the manifest | `scripts/check_deps.py` — modes: --imports |
| which emitter reads which palette authority | `scripts/check_token_source.py` — modes: --map |
| `segment_topology.py`'s exported API vs its consumers | `scripts/check_st_api.py` — modes: --used, --missing |
| whether the research pipeline imports | `scripts/check_consumers.py` — modes: --list |
| the browser theme's emitted manifests | `scripts/check_chrome.py` — modes: --dump |
| the partial-recovery record | `scripts/check_partial.py` — modes: --list |
| the claim graph / worklist status | `scripts/worklist_gate.py` — modes: --project, --discriminate, --where |
| the segment lattice's own invariants | `python3 segment_topology.py --selftest` |

## How to use one

**Run a tool bare to list its modes.** Every tool takes `--selftest`, refuses an unknown
flag rather than silently degrading to verbose-but-passing, and reports **n of m** rather
than a bare count — so an empty population is distinguishable from a clean result.

⚑ **A tool that finds nothing says which.** `check_compiles` refuses when its search
matches no files at all, because "0 failures over 0 files" and "0 failures over 24 files"
must not print the same thing. If you see a bare count anywhere, that is a bug.

## For dispatched agents

If you are answering a question about this repo, find its row above and run that tool.
If no row fits, say so plainly and **name the tool that should exist** — do not fall back
to grep and present the result as if it were the answer. The gap is the finding.
