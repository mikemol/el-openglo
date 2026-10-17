# Copyright 2026 Mike Mol
# Distributed under the terms of the Apache License, Version 2.0

EAPI=8

# Python is a BUILD tool here: the emitters solve the palette and write every
# surface at install time; nothing Python ships. Hence python-any-r1, and the
# solver's deps are BDEPEND.
PYTHON_COMPAT=( python3_{12..14} )
inherit git-r3 python-any-r1

DESCRIPTION="EL Openglo — an electroluminescent-display desktop theme, generated from one palette"
HOMEPAGE="https://github.com/mikemol/el-openglo"
EGIT_REPO_URI="https://github.com/mikemol/el-openglo.git"

LICENSE="Apache-2.0"
SLOT="0"
# 9999 has no KEYWORDS by convention (live ebuild): unmask it explicitly in
# package.accept_keywords with `x11-themes/el-openglo **`.
KEYWORDS=""

# The base set from pyproject.toml — what the CORE emission path needs. The
# `research`/`tooling` extras are not needed to emit the theme.
# qtdeclarative supplies qmllint and the qml runner that make_deb's QML-SANITY
# and RENDER-GATE steps use at staging time (W25); a runner that cannot start
# under the sandbox is a printed SKIP there, never a build failure.
BDEPEND="
	$(python_gen_any_dep '
		media-gfx/cairosvg[${PYTHON_USEDEP}]
		dev-python/colorspacious[${PYTHON_USEDEP}]
		dev-python/numpy[${PYTHON_USEDEP}]
		dev-python/pillow[${PYTHON_USEDEP}]
		dev-python/fonttools[${PYTHON_USEDEP}]
	')
	dev-qt/qtdeclarative:6
	media-fonts/liberation-fonts
"
# liberation-fonts: the marquee's Latin-1 dot-matrix glyphs are rasterised from
# Liberation Mono at BUILD time (make_notify_marquee.matrix_font, W6); without
# it the ticker ships the 70 authored glyphs only and every lowercase
# notification letter renders as '?'. A build input, so BDEPEND.
# What the installed surfaces run inside.
RDEPEND="
	kde-plasma/plasma-workspace:6
"

# ⚑ THE CVD CORE IS AN mtools DIST, NOT THIS TREE (W544): cvd_gate imports `mikemol.cvdcore`, and the
# sandbox python has no `mikemol` (the wheels live in repo venvs), so src_compile died with
# ModuleNotFoundError and luthen's host apply failed every pass (W560). The dist is stdlib plus numpy and
# colorspacious, both already BDEPEND, so the build takes its source from the SAME mtools commit the repo's
# pyproject.toml pins (mikemol-cvdcore @ ...@<sha>) and puts cvdcore/src on PYTHONPATH. Move the two together.
MTOOLS_COMMIT="6fba7de7f0ca5b887f1995eb80eb028b8dc7aeac"

src_unpack() {
	git-r3_src_unpack
	local EGIT_REPO_URI="https://github.com/mikemol/mtools.git"
	local EGIT_COMMIT="${MTOOLS_COMMIT}"
	local EGIT_CHECKOUT_DIR="${WORKDIR}/mtools"
	git-r3_src_unpack
}

python_check_deps() {
	python_has_version \
		"media-gfx/cairosvg[${PYTHON_USEDEP}]" \
		"dev-python/colorspacious[${PYTHON_USEDEP}]" \
		"dev-python/numpy[${PYTHON_USEDEP}]" \
		"dev-python/pillow[${PYTHON_USEDEP}]" \
		"dev-python/fonttools[${PYTHON_USEDEP}]"
}

src_compile() {
	# ⚑ THE PALETTE IS SOLVED HERE, NOT AUTHORED. make_schemes solves the grid on
	# import (~2 min, cached in .palette-cache.json inside ${S}) and the emitters
	# write every surface from it. Staging does both; this phase only warms the
	# cache so src_install's timing is honest.
	export PYTHONPATH="${WORKDIR}/mtools/cvdcore/src${PYTHONPATH:+:${PYTHONPATH}}"
	"${EPYTHON}" -c "import make_schemes" || die "palette solve failed"
}

src_install() {
	# ⚑ ONE STAGING, TWO PACKAGERS. make_deb.stage(root) lays the whole install
	# tree under a DESTDIR — the same function the Kubuntu .deb wraps — so the
	# set of files this ebuild installs cannot drift from the .deb's.
	# A render-gate SKIP under the sandbox is printed and is not an error.
	export PYTHONPATH="${WORKDIR}/mtools/cvdcore/src${PYTHONPATH:+:${PYTHONPATH}}"
	"${EPYTHON}" make_deb.py --stage "${ED}" || die "make_deb --stage failed"
	# make_deb stages helper scripts into usr/bin; make sure they are executable
	find "${ED}/usr/bin" -type f -exec chmod 0755 {} + || die
}

pkg_postinst() {
	elog "Apply a variant per user with:  el-openglo-apply EL-Openglo"
	elog "Boot splash (root):            el-openglo-plymouth EL-Openglo"
	elog "Six variants ship: EL-Openglo, EL-Azure, EL-Amber, and their -Lit backlit forms."
}
