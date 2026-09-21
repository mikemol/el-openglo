# Publishing — where each emission goes, and what the venue asks

Evidence: `inbox/2026-09-20-linux-sources-contribution-routes-per-target.md` (the
linux-sources session's letter, W13), the OCS category listing cached at
`catalog/ocs-categories.xml` (fetched from `api.kde-look.org/ocs/v1/content/categories`,
2026-09-21), MDN (Firefox), learn.microsoft.com (Windows), and this repo's own W12/W14/W16.
`scripts/check_publishing.py` holds this table to two facts it can measure: every
emitter has a row, and every KDE Store category id it cites exists in the cached listing.

Tags on the venue column are the letter's: **[OCS]** read from the store's API,
**[WEB]** a fetched page, **[MEM]** unverified, **[ABS]** looked for and absent.

## The table

| emitter | artifact | venue | category / route | xdg_type | licence gate | preview asset | status |
|---|---|---|---|---|---|---|---|
| make_schemes | `.colors` ×6 | KDE Store | id 112 "Plasma Color Schemes" [OCS] | plasma_color_schemes | store selector [MEM]; GPL-3 | make_preview preview.png | not submitted |
| make_plasma | Plasma style SVGs | KDE Store | id 104 "Plasma Themes" [OCS] | plasma5_desktopthemes (Plasma 6 goes here too) | GPL-3 | make_preview | not submitted |
| make_aurorae | Aurorae decorations | KDE Store | id 114 "Plasma Window Decorations" [OCS]; id 717 "Plasma 6 Window Decorations" has no xdg_type — try 114 first [MEM] | aurorae_themes | GPL-3 | decoration render | not submitted |
| make_deb (LnF) | Global Theme packages ×6 | KDE Store | id 722 "Global Themes (Plasma 6)" [OCS]; splash alone would be id 716 | — | GPL-3 | contents/previews/ (shipped in the package) | not submitted |
| make_konsole | Konsole `.colorscheme` + profile | KDE Store | id 462 "Konsole Color Schemes" [OCS] | — | GPL-3 | screenshot [MEM] | not submitted |
| make_konsole | Alacritty / foot / Windows Terminal / Termux | GitHub release assets | no venue has a category; the file is the install | — | GPL-3 | — | ships in the package |
| make_kvantum | Kvantum recolour | GitHub (tsujan/Kvantum PR) | NO OCS category [OCS ABS]; upstream states no criteria [ABS] | — | GPL-3 (KvFlat is GPL-3) | — | not submitted; emitter needs /tmp/KvFlat.kvconfig |
| make_chrome | Chrome theme manifests | Chrome Web Store | developer dashboard + one-time fee [WEB]; themes exempt from the item limit [WEB] | — | [ABS] | 128px icon + screenshots [MEM] | not submitted |
| make_firefox | Firefox theme manifests | addons.mozilla.org | unlisted signing is enough to install; listed optional (MDN) | — | AMO licence field | 32px icon optional | not submitted |
| make_plymouth | Plymouth themes ×6 | KDE Store | id 108 "Plymouth Themes" [OCS]; no upstream collection [MEM] | — | GPL-3 | boot render | not submitted |
| make_wallpaper | static wallpapers | KDE Store | id 299 "Wallpapers KDE Plasma" [OCS, read via `check_publishing --categories wallpaper`] | wallpapers (GHNS-installable) | GPL-3 | the image | not submitted |
| make_wallpaper_live | live wallpaper plugins | KDE Store | id 715 "Plasma 6 Wallpaper Plugins" [OCS] (not GHNS-installable: no xdg_type) | — | GPL-3 | screenshot | not submitted |
| make_clock | segment clock plasmoids | KDE Store | id 708 "Plasma 6 Clocks" [OCS] | plasma6_plasmoids | GPL-3 | screenshot (render_qml) | not submitted |
| make_notify_marquee | marquee plasmoids | KDE Store | id 706 "Plasma 6 Applets" [OCS] | plasma6_plasmoids | GPL-3 | screenshot | not submitted |
| make_css | `el-openglo.css` | the operator's site | consumed directly (W19) | — | — | — | ships |
| make_union | Union styles ×6 | none yet | Union has no theme venue in 6.7.5 (styles are found by UNION_STYLE_NAME) | — | GPL-3 | — | ships in the package |
| make_windows | `.theme` ×6 | GitHub release assets | Microsoft has no third-party theme venue | — | — | DesktopBackground png | ships in the package |
| make_deb | Kubuntu `.deb` | self-hosted | Debian discourages advertising uploads [WEB]; mentors.debian.net if a request appears | — | DFSG | — | self-hosted |
| overlay/ | Gentoo ebuild | own overlay (done, W12); GURU PR later [WEB] | codeberg.org/gentoo/guru, dev branch | — | `LICENSE=` in tree | — | overlay live |

## What is unverified, by name

The upload FORM — licence selector, preview requirements, whether Aurorae lands in 114 or
717 — is [MEM] throughout. One login answers it: the operator opening
`store.kde.org/product/add` once. Until then, every "not submitted" row is a plan, and the
check holds only the two facts it can reach.

## What no venue answered

Whether a GENERATED theme is welcome: [ABS] everywhere. The store links six uploads to
one palette through nothing but the author field.
