# SPDX-License-Identifier: Apache-2.0
"""scripts — the gates, checks and generators this repo's commit path runs.

⚑ A MARKER, NOT A FACADE — no re-exports.  It exists because the borrowed hooks
(symlinks into ../substrate, see CLAUDE.md "Borrowed tooling") do
`from scripts import hook_cmdparse`: substrate promoted its shared tokenizer into a
package-relative import, and a symlinked hook resolves `scripts` against THIS tree
(`Path(__file__).absolute()` does not follow the link).  Without this file the hooks
import-fail before they read a single byte of this repo's data, which
`check_hooks.py` reports as 2 of 2 selftests failed.  Modules stay addressed by name.
"""
