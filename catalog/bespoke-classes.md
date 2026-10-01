# Bespoke classes: what is authored, what must be emitted

The class table behind W120 ("nothing bespoke", operator 2026-09-28): every tracked file is either
AUTHORED source, PRODUCED by a named emitter, or a LIFT DEBT naming its waypoint; anything else is
an orphan. `scripts/check_bespoke.py` (W191) will read this table; `policy/bespoke.rego` (W192)
denies an orphan. **Draft for operator confirmation (W190): nothing is denied until it is
confirmed.**

Census source: `scripts/build_graph.py` (2026-10-01; it refuses with 329 indeterminate relations,
so its 194 orphans are an upper bound) and `git ls-files`.

| kind | example | class | producer / owner | confidence |
|---|---|---|---|---|
| Python source | `make_*.py`, `scripts/*.py` | AUTHORED | | certain |
| QML / JS templates | `templates/*.qml`, `templates/*.js` | AUTHORED | the emitters substitute into them | certain |
| kcfg templates | `templates/*-config.kcfg` | AUTHORED | | certain |
| Rego policies and tests | `policy/*.rego`, `policy/*_test.rego` | AUTHORED | | certain |
| Hand-written docs | `CLAUDE.md`, `catalog/*.md`, `.claude/vector-calibration.md` | AUTHORED | | certain |
| Claim graphs | `catalog/**/warrants.bib`, `catalog/library/concepts.bib` | AUTHORED | | certain |
| Projected docs | `WORKLIST.md`, `README.md` | PRODUCED | `scripts/worklist_gate.py --project` (paperkit) | certain |
| Queue mirror | `.claude/paths-forward.md` | PRODUCED | `mikemol-paths-forward` (render on every write) | certain |
| Queue state | `.claude/paths-forward.json`, `.ledger` | STATE | `mikemol-paths-forward` (the one writer) | certain; neither authored nor an asset |
| Colour schemes | `EL-*.colors` (6) | PRODUCED | `make_schemes.py` (`catalog/actions.json`: schemes) | certain |
| Wallpapers | `*-wallpaper.png`, `*-wallpaper.svg` (12) | PRODUCED | `make_wallpaper.py` (`catalog/actions.json`: wallpapers) | certain |
| Screenshots | `catalog/library/screens/*.png` (55) | PRODUCED | `catalog/library/render_screens.py` (`actions.json`: screens) | certain |
| Library samples | `catalog/library/samples/*.svg`, `splash-digits.png` | PRODUCED | `catalog/library/render_samples.py` | likely; not in `actions.json`, so not currency-keyed |
| Parity baselines | `catalog/baselines/*` (15) | PRODUCED | `check_template_parity.py --record` from the emitters | certain; a recorded snapshot, refreshed on intent |
| Build keys | `catalog/actions.json` | PRODUCED | `check_action_key.py --write` | certain |
| Clock package | `plasma-clock/org.el.segclock/**` (6) | ? | tracked emitter output, or a hand-kept copy? | **unknown: operator** |

## Questions for the operator

1. **`plasma-clock/`**: is this tracked directory an emitter's output that should be regenerated
   (and then either produced-and-checked or untracked), or a hand-kept copy that is LIFT DEBT?
2. **Library samples** are produced but not currency-keyed. Should they join `catalog/actions.json`
   so a stale sample is caught the way a stale screenshot is?
3. **Parity baselines** are snapshots recorded from the emitters by intent. Is PRODUCED the right
   class, or should they be their own class (RECORDED) so the check never demands they match the
   current emitter?
