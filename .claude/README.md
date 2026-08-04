# `.claude/` — harness wiring

## The two PreToolUse hooks are ADVISORY here, deliberately

`settings.json` wires both hooks but **omits** the env vars that arm them:

    STRUCT_HOOK_BLOCK=1     # would make hook_structural_query.py REFUSE
    NOCHAIN_HOOK_BLOCK=1    # would make hook_no_chaining.py REFUSE

Upstream ships them armed to deny. Borrowing that here on day one would refuse an
ordinary `grep somefile.py` and every `cmd1 && cmd2` before anyone had measured the
false-positive rate against *this* repo's shape — and both hooks' own docstrings argue
for advisory-first sequencing.

**Arm them by adding an `env` block once the routing table has covered a few weeks of
real questions:**

    "env": { "STRUCT_HOOK_BLOCK": "1", "NOCHAIN_HOOK_BLOCK": "1" }

⚑ Arming the structural hook is only meaningful while
`.claude/skills/struct-tools/SKILL.md` has rows. A hook that fires with an empty table
refuses without naming the owning tool, which teaches nothing —
`scripts/check_routes.py` is the claim that guards against exactly that.

## The hooks are symlinks

`scripts/hook_no_chaining.py` and `scripts/hook_structural_query.py` point into
`../../substrate/scripts/`. **Editing one edits substrate.** Change it there, and run
both repos' selftests before committing. `scripts/check_hooks.py --list` shows where each
currently resolves.

They read their data from THIS repo (each derives its root from `__file__`, and
`os.path.abspath` does not resolve symlinks), which is what makes sharing the code
correct — but it is also why the routing table must be a real local file rather than a
symlink to substrate's.
