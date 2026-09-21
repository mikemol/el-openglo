# Copyright 1999-2024 Gentoo Authors
# Distributed under the terms of the GNU General Public License v2
#
# Carried verbatim from ::guru (dev-python/colorspacious-1.1.2, 2026-09-21) so
# that x11-themes/el-openglo's BDEPEND resolves on a host WITHOUT guru enabled.
# cvd_gate.py needs it for the CVD simulation; nothing else in ::gentoo provides
# it. Drop this copy when ::gentoo or the host carries it.
EAPI=8

DISTUTILS_USE_PEP517=setuptools
PYTHON_COMPAT=( python3_{12..15} )

inherit distutils-r1 pypi

DESCRIPTION="Python library for doing colorspace conversions"
HOMEPAGE="
	https://pypi.org/project/colorspacious/
	https://github.com/njsmith/colorspacious
"

LICENSE="MIT"
SLOT="0"
KEYWORDS="~amd64 ~arm64"

RDEPEND="
	dev-python/numpy[${PYTHON_USEDEP}]
"
