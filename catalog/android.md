# Android — what of the palette reaches a phone, and through what

Android apps do not read a theme file. Material You (Monet) derives its own tonal
palette from a **seed colour** — the wallpaper's, or one the launcher picks — and
apps read that. So the honest emit is a wallpaper plus a *documented seed*, and the
only claim worth making is whether Monet, seeded from this palette, lands where the
palette's relations say it should. `scripts/check_monet.py` runs Google's reference
implementation (`material-color-utilities` 0.2.6, the `research` extra; TonalSpot at
contrast 0 — what the system applies by default) over each variant seeded from its
**lit** colour. Measured 2026-09-21:

| variant | scheme | Monet surface vs ground (dE) | primary hue Δ from seed | on_surface / surface | on_primary / primary |
|---|---|---|---|---|---|
| EL-Openglo | dark | 3.0 | 0.3° | 14.35 | 7.73 |
| EL-Azure | dark | 3.4 | 0.2° | 14.28 | 7.71 |
| EL-Amber | dark | 2.5 | 0.1° | 14.35 | 7.74 |
| EL-Openglo-Lit | light | 8.2 | 0.2° | 16.31 | 6.43 |
| EL-Azure-Lit | light | 21.5 | 0.7° | 16.27 | 6.44 |
| EL-Amber-Lit | light | 17.0 | 0.0° | 16.28 | 6.48 |

## What agrees, and is claimed (`@MONET`)

- **The hue survives**: Monet's primary keeps the seed's HCT hue to under 1° on all six.
- **Every text pair Monet makes clears AA** — seeding from this palette yields a usable
  scheme; nothing the phone draws with it is unreadable.
- **On the Off variants, Monet's dark surface lands within 2.5–3.4 dE of our ground.**
  A phone seeded from EL-Azure's lit colour draws its surfaces in EL-Azure's void.

## What disagrees, and is recorded rather than smoothed

- **The Lit variants' ground cannot be reached.** Monet's light surfaces are
  near-white by construction (tone 98); ours are backlit phosphor (`#9de8d8`). dE
  8–21. A Lit variant on a phone is a hue, not a ground.
- **Monet's primary is not our lit.** TonalSpot clamps chroma to 36 and picks tone 80
  (dark) / 40 (light); EL-Openglo's primary is `#83d5c5` against a lit of `#99ffeb`
  (dE 12). The relation that holds is hue, not colour.
- **on_surface is Monet's neutral, not our phosphor text** (dE up to 17 on Azure).
  Android body text will be near-white on the void, not phosphor-tinted.

## The emit

`usr/share/el-openglo/wallpapers/` (the static wallpaper already ships) plus the seed
per variant, which is the variant's lit colour — the wallpaper's own dominant colour
extraction (`prominent_colors_from_image`) is a second route the check does not yet
measure. The terminal side ships already: `<variant>.termux.properties` (W16).

Not built, with reasons: themed icons (Android draws them in Monet's own primary; no
input of ours); a launcher theme (no cross-launcher format exists).
