# Notification capabilities on the marquee (W46)

The marquee reads Plasma's public notification model (`org.kde.notificationmanager`,
the feed the stock applet reads). Its contract on this host is MEASURED, not
remembered: `scripts/check_notify_roles.py` parses the module's qmltypes — 49
roles, the `Urgency` / `Type` / `JobState` enums, `invokeAction` — and
`policy/notify_roles.rego` holds every role a capability reads to be declared by
the host (N2) and modelled by the headless stub (N3), so a capability cannot be
written against a role the harness is blind to. The numbers the tool prints are
declaration ordinals; the widget reads roles symbolically.

Operator, 2026-09-22, with the notify-send man page open: "which are we not
achieving?" This table is the answer, one row per capability, each stated as a
relation on the board (relations.md §5a hue, §5b brightness) before any code.

| capability | role(s) | on the board | status |
|---|---|---|---|
| identity, text | `IdRole` `SummaryRole` `BodyRole` `ApplicationNameRole` | the queue keyed by id; summary plain, body parsed to runs (W39/W45) | shipped (s89-s103) |
| urgency | `UrgencyRole` (Low 0 / Normal 1 / Critical 2) | critical: painted in the HOT token (`Kirigami.Theme.activeTextColor`, the ink colour the field reads back) and re-queued while it lives — it keeps cycling until dismissed; normal: as now; low: dimmer ink (the aperture makes weight a number: coverage scaled, γ untouched) | next |
| expiry | `ExpiredRole` | drops at the next boundary only (W45); critical ignores it, as Plasma does | shipped (boundary); critical rule with urgency |
| replace | (same id, new data) | the id-keyed queue upserts; the new text scrolls once more (W45) | shipped |
| transient | `TransientRole` | exactly one traversal — the queue's `shown` flag, never re-queued | with urgency |
| actions | `ActionNamesRole` `ActionLabelsRole` + `invokeAction(index, id)` | rendered as tappable underlined runs after the text (`[Reply] [Open]`); a tap hit-tests to the run and calls `invokeAction` — the board becomes interactive | after urgency |
| job progress | `PercentageRole` `JobStateRole` `TypeRole` (Job 2) | a GAUGE: the percentage history as a series (W48's `seriesToColumns`) painted into the backdrop — one column per sample, the newest at the right — beside the job's text; suspended dims, stopped drops at the boundary | after actions |
| category | `CategoryRole` | a style rule per category (e.g. `device.*` → the field's ring flashes once) | later |
| hints | `HintsRole` | read for `value` (progress) and `urgency` fallbacks; otherwise carried, unread | later |
| icons | `ImageRole` `IconNameRole` | an icon raster is a BACKDROP through the viewport (⊕APERTURE-FIELD; W47's fold) — the app icon rasterised at runtime into column bytes; the app name stands in until then | later |
| reply | `HasReplyActionRole` `ReplyActionLabelRole` … `reply()` | a text field is not a matrix's affordance; the reply action is offered as an action run that opens the stock popup | not planned |

What a capability may NOT do: paint a sender's literal colour (§5a), snap a pip
(§5b), rebuild the board mid-scroll (W38/W45), or read a role the stub lacks (N3).
