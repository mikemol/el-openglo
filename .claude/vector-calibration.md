# WV:1 calibration for el-openglo

How this repo's waypoints are scored (`--vector`, `--vector-source agent`). The grammar is
mtools' `pathsforward/vector.py`; the bands are nemik's `data/bands.toml`. This file records the
JUDGEMENT that maps an el-openglo item onto that grammar, so a score can be audited and re-derived
instead of re-guessed. First applied 2026-10-01 to the 85 open waypoints (operator: "you've got a
population to score").

## The metrics, read for a desktop theme

| metric | value | in this repo |
|---|---|---|
| R reach | L | the repo: tooling, gates, queue, emitters whose output is not yet installed |
| | H | the operator's desktop: a shipped surface (marquee, clock, wallpaper, SDDM, plymouth), the install path, or a harness that can disturb the live session |
| | T, C | not used: el-openglo has no tenants or cluster |
| E egress | Y | content leaves the host: publishing to a store (AMO, Chrome Web Store, KDE Store) |
| C confidentiality | L | handles credentials or the operator's local data (API keys, metrics) |
| | H | not used here; W176 (notification content in logs) was the precedent, now done |
| I integrity | N | bookkeeping with no effect on output or verdicts (reports, cleanup) |
| | L | output or a verdict can be wrong: an emitter, a gate, a measurement |
| A availability | L | a shipped surface degrades but the desktop works |
| | H | a shipped surface fails to load or stays broken (W83, W92) |
| X precondition | P | blocked on another waypoint, repo or the operator; N when ready |
| S scope | U | always, so far. C would put the item in nemik's trust-boundary policy class, which BLOCKS every ready item sharing a touches tag; no open item crosses a trust boundary the way W176 did |
| F fix known | K | the next step is concrete; U when it is research or the mechanism is unknown |
| W witness | Y | a gate/check already exists that will show it done; N when the witness is part of the work |

## Resulting bands

- **normal**: almost everything (R:L or R:H with I:L, no S:C).
- **elevated**: A:H — an operator-visible load failure (W83, W92).
- **low**: R:L with no C/I/A impact — reports, cleanup, asks (W95, W97, W102, W106, W115, W138).
- **high / critical**: none open. They need S:C, C:H, I:H or R:C, which no open item has.

## Residue

- W65 ("66 of 72 checks grade indeterminate") could be argued I:H, since it is about whether the
  whole verification means anything. Scored I:L to stay consistent with every other gate item;
  revisit if the operator wants verification-integrity items above normal.
- The publishing items (W41, W136, W137) egress and touch credentials, but are scored S:U: the
  operator holds the keys, and S:C would block unrelated ready work through the policy class.
