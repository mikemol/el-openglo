# `.claude/` — harness wiring

## The two PreToolUse hooks are ARMED

`settings.json` sets both env vars, so the hooks REFUSE rather than merely comment:

    STRUCT_HOOK_BLOCK=1     # hook_structural_query.py denies
    NOCHAIN_HOOK_BLOCK=1    # hook_no_chaining.py denies

⚑ **ADVISORY MODE IS SILENT TO THE AGENT, NOT MERELY NON-BLOCKING — and this file
previously said otherwise.** Unarmed, a hook prints its advisory and exits 0 with no
`permissionDecision`, which the harness reads as *allow, nothing to report*: the text
reaches nobody. So the choice is not "soft guard vs hard guard", it is "guard vs no
guard". These were wired advisory at first on the reasoning that the false-positive
rate should be measured before arming — but nothing measured it, and an indefinite
deferral with a plausible reason attached is how an exemption swallows a rule. The
violations that mode let through were real ones, caught by a human instead.

⚑ **ARMING ALONE IS HALF THE PATTERN.** `settings.local.json` carries the per-tool
allowlist. Armed hooks push you toward a single named tool call; the allowlist is what
makes that call run without a permission prompt every time. Without it you refuse the
chain and then prompt on its replacement, which teaches people to disarm the hook.
**Add a row there whenever you add a tool** — a tool nobody can run without a prompt
is a tool that loses to `grep`.

⚑ Arming the structural hook is only meaningful while
`.claude/skills/struct-tools/SKILL.md` has rows. A hook that fires with an empty table
refuses without naming the owning tool, which teaches nothing —
`scripts/check_routes.py` is the claim that guards against exactly that.

**If a refusal is a genuine false positive**, the fix is a new mode on the owning tool
(and its row in the table), never standing the hook down. A missing mode is WORK.

## The hooks are symlinks

`scripts/hook_no_chaining.py` and `scripts/hook_structural_query.py` point into
`../../substrate/scripts/`. **Editing one edits substrate.** Change it there, and run
both repos' selftests before committing. `scripts/check_hooks.py --list` shows where each
currently resolves.

They read their data from THIS repo (each derives its root from `__file__`, and
`os.path.abspath` does not resolve symlinks), which is what makes sharing the code
correct — but it is also why the routing table must be a real local file rather than a
symlink to substrate's.
