# Publishing — where each emission goes, and what the venue asks

Evidence: `inbox/2026-09-20-linux-sources-contribution-routes-per-target.md` (the
linux-sources session's letter, W13), the OCS category listing cached at
`catalog/ocs-categories.xml` (fetched from `api.kde-look.org/ocs/v1/content/categories`,
2026-09-21), the operator's saved copy of `store.kde.org/product/add`'s Basics step
(2026-09-27 — the licence list, the logo/gallery size limits, and the category picker
being a client-side widget that does not appear in a static save), MDN (Firefox),
learn.microsoft.com (Windows), and this repo's own W12/W14/W16.
`scripts/check_publishing.py` holds this table to two facts it can measure: every
emitter has a row, and every KDE Store category id it cites exists in the cached listing.

Tags on the venue column are the letter's: **[OCS]** read from the store's API,
**[WEB]** a fetched page, **[MEM]** unverified, **[ABS]** looked for and absent.

## The table

| emitter | artifact | venue | category / route | xdg_type | licence gate | preview asset | status |
|---|---|---|---|---|---|---|---|
| make_schemes | `.colors` ×6 | KDE Store | id 112 "Plasma Color Schemes" [OCS] | plasma_color_schemes | Apache License and GPLv3 both listed [WEB] | make_preview preview.png | not submitted |
| make_plasma | Plasma style SVGs | KDE Store | id 104 "Plasma Themes" [OCS] | plasma5_desktopthemes (Plasma 6 goes here too) | GPL-3 | make_preview | not submitted |
| make_aurorae | Aurorae decorations | KDE Store | id 114 "Window Decoration Aurorae" [OCS, `xdg_type=aurorae_themes` — CONFIRMED [WEB]: id 717 "Plasma 6 Window Decorations" carries no `xdg_type` and is the newer native-decoration bucket; the live category picker (2026-09-27) lists both as distinct, populated categories under the same breadcrumb (114-equivalent "Plasma Window Decorations" 687 products; 717-equivalent "Plasma 6 Window Decorations" 230 products) — matched by exact display-name text, since the picker's static HTML never exposes the numeric id itself, only on server-side selection] | aurorae_themes | GPL-3 | decoration render | not submitted |
| make_deb (LnF) | Global Theme packages ×6 | KDE Store | id 722 "Global Themes (Plasma 6)" [OCS]; splash alone would be id 716 | — | GPL-3 | contents/previews/ (shipped in the package) | not submitted |
| make_konsole | Konsole `.colorscheme` + profile | KDE Store | id 462 "Konsole Color Schemes" [OCS] | — | GPL-3 | screenshot, within 5 MB / 5-picture Gallery limit [WEB] | not submitted |
| make_konsole | Alacritty / foot / Windows Terminal / Termux | GitHub release assets | no venue has a category; the file is the install | — | GPL-3 | — | ships in the package |
| make_kvantum | Kvantum recolour | GitHub (tsujan/Kvantum PR) | NO OCS category [OCS ABS]; upstream states no criteria [ABS] | — | GPL-3 (KvFlat is GPL-3) | — | not submitted; emitter needs /tmp/KvFlat.kvconfig |
| make_chrome | Chrome theme manifests | Chrome Web Store | developer dashboard + one-time fee [WEB]; themes exempt from the item limit [WEB] | — | [ABS] | 128px icon + screenshots [MEM] | not submitted |
| make_firefox | Firefox theme manifests | addons.mozilla.org | unlisted signing is enough to install; listed optional (MDN) | — | AMO licence field | 32px icon optional | not submitted |
| make_plymouth | Plymouth themes ×6 | KDE Store | id 108 "Plymouth Themes" [OCS]; no upstream collection [MEM] | — | GPL-3 | boot render | not submitted |
| make_wallpaper | static wallpapers | KDE Store | id 299 "Wallpapers KDE Plasma" [OCS, read via `check_publishing --categories wallpaper`] | wallpapers (GHNS-installable) | GPL-3 | the image | not submitted |
| make_wallpaper_live | live wallpaper plugins | KDE Store | id 715 "Plasma 6 Wallpaper Plugins" [OCS] (not GHNS-installable: no xdg_type) | — | GPL-3 | screenshot | not submitted |
| make_clock | segment clock plasmoids | KDE Store | id 708 "Plasma 6 Clocks" [OCS] | plasma6_plasmoids | GPL-3 | screenshot (render_qml) | not submitted |
| make_notify_marquee | marquee plasmoids | KDE Store | id 706 "Plasma 6 Applets" [OCS] | plasma6_plasmoids | GPL-3 | screenshot | not submitted |
| make_font | EL-Segment-{7,16}.ttf, EL-Matrix-5x7.ttf (+ SVG fonts) | GitHub release assets — the KDE Store listing has NO font category (`check_publishing --categories font`: 0 of 167) [OCS ABS] | — | GPL-3 (glyphs are the substrate's) | specimen render (check_font --render) | ships in the package |
| make_gtk | gtk3.css / gtk4.css ×6 | gnome-look.org (GTK3/4 Themes category) [MEM] — or the user's `~/.config/gtk-{3,4}.0/gtk.css` via el-openglo-apply | — | GPL-3 | screenshot | ships in the package |
| make_css | `el-openglo.css` | the operator's site | consumed directly (W19) | — | — | — | ships |
| make_union | Union styles ×6 | none yet | Union has no theme venue in 6.7.5 (styles are found by UNION_STYLE_NAME) | — | GPL-3 | — | ships in the package |
| make_windows | `.theme` ×6 | GitHub release assets | Microsoft has no third-party theme venue | — | — | DesktopBackground png | ships in the package |
| make_deb | Kubuntu `.deb` | self-hosted | Debian discourages advertising uploads [WEB]; mentors.debian.net if a request appears | — | DFSG | — | self-hosted |
| overlay/ | Gentoo ebuild | own overlay (done, W12); GURU PR later [WEB] | codeberg.org/gentoo/guru, dev branch | — | `LICENSE=` in tree | — | overlay live |

## What is unverified, by name

Resolved 2026-09-27 (operator opened `store.kde.org/product/add`'s Basics step):

- **Licence selector**: lists AGPLv3, Apache License, BSD License, CC0, CC-BY, CC-BY-SA,
  GFDL, GPLv2-only, GPLv2-or-later, GPLv3, LGPLv2, LGPLv3, MIT, MRR, PLR and SIL OFL. Every
  licence this repo actually ships under (Apache-2.0, GPL-3 for the GPL-derived emitters)
  is accepted.
- **Preview assets**: Product Logo min 20×20, max 2000×2000, max 2MB. Gallery Pictures:
  max 5MB total, max 5 pictures.
- **Aurorae's category**: 114, not 717 — see the make_aurorae row. A second saved copy of
  the page (2026-09-27, with the category picker expanded) shows the live, product-count-
  ranked tree; "Plasma Window Decorations" (687 products, matching id 114's display_name)
  and "Plasma 6 Window Decorations" (230 products, matching id 717's) are both real,
  actively-used categories under the same breadcrumb — not one legacy and one current —
  which corroborates the `xdg_type` reasoning rather than resting on it alone. The picker's
  static HTML carries no `aurorae` string and no visible numeric id (0 hits searched); the
  match is by exact display-name text against `catalog/ocs-categories.xml`, not a byte-exact
  id readback, which is the honest limit of what a saved page can confirm here.

Still open: the category-tree WIDGET behind the "Change" button resolves ids server-side on
selection, so the Plasma 6 Applets/Clocks/etc. ids this table already cites from the cached
OCS listing (`catalog/ocs-categories.xml`) remain [OCS]-sourced by title-match, not by a
captured numeric id. That is lower-stakes than the three questions above: the OCS listing
IS the same taxonomy the picker reads from, and its titles agree everywhere checked so far.

Every "not submitted" row is still a plan — nothing has been uploaded — and the check
holds only the two mechanical facts it can reach (row coverage, id existence).

## What no venue answered

Whether a GENERATED theme is welcome: [ABS] everywhere. The store links six uploads to
one palette through nothing but the author field.
