# `.claude/` — harness wiring

## The two PreToolUse hooks are ARMED, on the COMMAND LINE

    "command": "NOCHAIN_HOOK_BLOCK=1 python3 \"$CLAUDE_PROJECT_DIR/scripts/…\""

⚑ **THE `env` BLOCK ALONE WAS NOT ENOUGH, AND I REPORTED IT AS ARMED FOR SEVERAL
COMMITS.** `settings.json` also declares these under `env`, which is correct and
insufficient: a session already running when the file changed never picks them up,
so the hooks kept exiting 0 — detecting every violation and reporting none. The
declaration was true and the behaviour was unchanged, which is the worst pairing:
a guard that reads as armed in review and is off in fact.

Measured, not assumed: `env | grep HOOK` in the tool's own shell showed both
UNSET while `settings.json` plainly set them. **Verify a guard by making it FIRE,
never by reading the file that configures it** — the same discipline the repo
applies to claims, applied to its own wiring.

Setting the variable on the command line removes the dependency on session
environment entirely. The `env` block stays for new sessions and as documentation
of intent; the command line is what makes it true in this one.

To confirm at any time, feed a violation to a hook and look for `permissionDecision`:

    printf '%s' '{"tool_name":"Bash","tool_input":{"command":"a | b"}}' \
      | NOCHAIN_HOOK_BLOCK=1 python3 scripts/hook_no_chaining.py

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
