# SPDX-License-Identifier: Apache-2.0
# The module catalog/fixtures/deps/undeclared.py imports on purpose (the W75 negative fixture for
# policy/deps.rego: a dependency absent from pyproject.toml). It does not exist at run time and the
# fixture is never imported; this stub lets the type checker resolve the name WITHOUT declaring the
# dependency anywhere check_deps.py looks (pyproject.toml), so the fixture still refuses (W255).
