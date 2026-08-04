# el-openglo — working instructions

A generated desktop theme: one palette, solved once, emitted to every surface. Also a
**recovery** — the original repo was lost before it was ever pushed, so parts of this
tree are replayed transcripts rather than authored source. That history is why the
discipline below is mechanical rather than remembered.

## THE STANDING RULE: fix the tooling so it answers your question

**If you have a question the tooling doesn't answer directly, fix the tooling so it
answers your question.** No complex command lines, no greps, no seds, no judgements not
in code. Use the tool that enables STRUCTURAL instead of TEXTUAL queries. **Don't have
the tool yet? Extending your tools is fixing your tools.**

`.claude/skills/struct-tools/SKILL.md` is the entrypoint — it carries the
`artifact → tool` table, and it is the LIVE table the PreToolUse hook parses.

Two failure shapes this exists to stop:

- **Reasoning not codified.** Needing more than ONE tooling command, or manipulating a
  tool's output (`| tail`, a `python3 -c` wrapper, a shell `case` over an error string),
  means the judgement is happening in the turn instead of in a program. It evaporates
  when the turn ends and the next reader re-derives it — differently.
- **Reading a toolkit gap as a category.** "No tool covers this, so grep is legitimate
  here" is a fact about the METHOD reported as a fact about the SUBSTRATE — the same
  error as reading *no match found* as *no such thing exists*. **An exception admitted
  for the uncovered case is the loophole that swallows the rule**, so there are no
  exceptions, only tools that do not exist yet.

⚑ **A missing mode is WORK, not a finding.** The honest response to "the tool can't
answer that" is to add the mode, not to route around it.

## The worklist is the status; nothing records status

`catalog/worklist/` is a claim graph run by **paperkit** (an engine at
`~/github/paperkit`, LOCATED not vendored — `scripts/worklist_gate.py` owns where it
lives, which entry point to call, and which directory is the project).

    python3 scripts/worklist_gate.py              # are all cited claims discharged?
    python3 scripts/worklist_gate.py --project    # regenerate WORKLIST.md
    python3 scripts/worklist_gate.py --discriminate  # Δ: can each check actually FAIL?
    python3 scripts/worklist_gate.py --where      # where engine + project resolved

⚑ **THERE IS NO open/closed FIELD, AND THERE MUST NEVER BE ONE.** An item is OPEN
exactly when its check exits non-zero, recomputed every run. "Open item" and "red check"
are one state. Nothing records status, so nothing about status can go stale.

**This repo is the argument for that rule.** `RECOVERY-NOTES.md` called the segment API
"the main rebuild gap" long after most of it had been recovered — a hand-written status
that decayed into a false claim. Measured, only three symbols were actually missing.

⚑ **`WORKLIST.md` IS GENERATED. Never hand-edit it** — the gate refuses drift between
the prose and its projection. Edit `warrants.bib`, then `--project`.

⚑ **NO CHECK MAY BE UNFALSIFIABLE.** paperkit's Δ grader marks a check that cannot fail
`indeterminate` or `vacuous`. An always-true check (`cmd:true`, a `premise:` verb) is an
unfalsifiable-claim factory: the gate certifies it and Δ cannot grade it. A decision item
is CLOSED while decided — it must not block — but its witness must still discriminate on
something (e.g. whether the decision is legible). Not-blocking and not-falsifiable are
separable; every item needs the first without the second.

## Writing a check

Every tool in `scripts/` follows the same shape, and a new one should too:

- **`--selftest`** that proves the check can SEE what it looks for. A scan whose
  all-clear has never been shown to differ from its found-something is not a measurement.
- **Refuse an unknown flag.** A gate that accepts `--queit` and exits 0 looks like it ran.
- **Report `n of m`, never a bare count.** "0 failures over 0 files" and "0 failures over
  24 files" must not print the same thing — if the population is empty, REFUSE: the
  search is broken, not the tree clean.
- **A missing optional dependency is a SKIP, counted and printed** — a fact about the
  machine, not about the artifact. **Not confirmed is not failed.**
- **State the weakness in the docstring.** `check_compiles` says outright that compiling
  proves syntax and nothing else, because all eight partial files compile.

## Borrowed tooling: some scripts are SYMLINKS into ../substrate

`scripts/hook_no_chaining.py`, `hook_structural_query.py`, `ratchet.py`,
`gate_ledger.py`, `run_selftests.py`, and `.githooks/pre-push` point into
`../../substrate/`. **Editing one edits substrate.** Change it there and run BOTH repos'
selftests. `scripts/check_hooks.py --list` shows where each resolves.

They read their data from THIS repo (each derives its root from `__file__`, and
`os.path.abspath` does not resolve symlinks), which is what makes sharing the code
correct — and is why `.claude/skills/struct-tools/SKILL.md` must be a REAL local file.
Symlinked to substrate's, it would route this repo's questions to Agda tools that do not
exist here; ABSENT, the hook fires naming no tool at all. Measured, before adoption.

The two PreToolUse hooks are wired **advisory**, not blocking — see `.claude/README.md`
for why, and for how to arm them.

## Commit policy

Work and commit on `main`; the pre-commit hook is the promotion gate. After `git commit`
the post-commit hook AMENDS the commit to fold in the advisory — **wait for the marker
`post-commit advisory (auto-captured)` in HEAD before pushing** (`pre-push` blocks a tip
without it), then fetch and fast-forward.

## Reuse-search BEFORE building new machinery

Before adding a generator, a checker, or a palette derivation, name the existing thing it
specialises. The emission targets all read ONE palette through two authorities
(`make_preview.parse_scheme`, `make_schemes.GRID`) — a new target that computes its own
colours silently stops matching when the palette is re-solved. That is not hypothetical:
`make_wallpaper.py`, the oldest generator, was doing exactly that, and
`scripts/check_token_source.py` found it on the check's first run.

⚑ **The absence-words ARE the trigger.** Before writing that something is *missing /
absent / not recoverable / impossible / the only*, run the tool that would know. The
recovery notes' stale "main rebuild gap" is what that failure looks like in this repo,
and `check_st_api.py --missing` is the tool that settles it in one command.
