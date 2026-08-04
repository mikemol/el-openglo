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

⚑ **FOUR COLUMNS, AND THE LAST ONE IS LOAD-BEARING.** `claims` declares which file
suffixes a tool owns. The hook no longer carries a hardcoded suffix list — it reads
this column — so a suffix claimed by no row is a suffix the hook will not guard, and
adding a tool without filling this in leaves its artifacts unprotected.

⚑ **SUBSTRATE PROVIDES THE GENERAL READERS; USE THEM.** Python, markdown and BibTeX
already have structural readers in `../substrate/scratch/`, built precisely because
someone kept reaching for `grep` at them. Do not grep those artifacts here and do not
reimplement a reader for them — point outward, exactly as the two PreToolUse hooks do.
This repo's own `check_*.py` answer questions about THIS project (is the mark gone, do
the emitters agree on one palette); they are not general readers and do not replace these.

| artifact | tool | run bare to list its modes | claims |
|---|---|---|---|
| Python — structure of any module | `../substrate/scratch/pycodemod.py` | `python3 ../substrate/scratch/pycodemod.py` | `.py` `.pyi` |
| markdown — headers, tables, cells | `../substrate/scratch/mdstruct.py` | `python3 ../substrate/scratch/mdstruct.py` | `.md` |
| BibTeX — the claim-DAG, not its text | `../substrate/scratch/bibstruct.py` | `python3 ../substrate/scratch/bibstruct.py` | `.bib` |
| this repo's Python: does it compile / import | `scripts/check_compiles.py` + `scripts/check_consumers.py` | `python3 scripts/check_compiles.py --list` | — |
| the claim graph's STATUS (are claims discharged) | `scripts/worklist_gate.py` | `python3 scripts/worklist_gate.py --where` | — |
| the design log's symbols, closures and open set | `scripts/cotype_index.py` | `python3 scripts/cotype_index.py` | — |
| Plasma / Konsole colour schemes | `scripts/check_selection_contrast.py` | `python3 scripts/check_selection_contrast.py --report` | `.colors` `.colorscheme` |
| the retired trademark, anywhere in the tree | `scripts/check_mark.py` | `python3 scripts/check_mark.py --files` | — |
| third-party imports vs the manifest | `scripts/check_deps.py` | `python3 scripts/check_deps.py --imports` | `.toml` |
| which emitter reads which palette authority | `scripts/check_token_source.py` | `python3 scripts/check_token_source.py --map` | — |
| `segment_topology.py`'s exported API vs its consumers | `scripts/check_st_api.py` | `python3 scripts/check_st_api.py --used` | — |
| the browser theme's emitted manifests | `scripts/check_chrome.py` | `python3 scripts/check_chrome.py --dump` | `.json` |
| the partial-recovery record | `scripts/check_partial.py` | `python3 scripts/check_partial.py --list` | — |
| the segment lattice's own invariants | `segment_topology.py` | `python3 segment_topology.py --selftest` | — |
| Agda source (`ELProjection.agda`) | `../substrate/scratch/agda_defs.py` + `agda_lex.py` | `python3 ../substrate/scratch/agda_defs.py <name>` | `.agda` `.agdai` `.lagda` |

⚑ **THE AGDA ROW POINTS OUT OF THIS REPO, AND THAT IS CORRECT.** `ELProjection.agda`
models this system in substrate's F₂ vocabulary, and substrate *provides* the readers for
that artifact kind — the same relationship as the two PreToolUse hooks. A tool is named
by where it lives, not by which repo happens to hold the file it reads; reimplementing an
Agda reader here to avoid pointing outward would be the reuse-search miss the standing
rule warns about.

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
