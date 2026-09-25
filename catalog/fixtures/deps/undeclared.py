"""W75 negative fixture for policy/deps.rego: an import neither declared in
pyproject.toml nor recorded there as absent, buried in a function body — the
shape `qml_sanity` reached the tree in. Never imported; only walked, when
planted by `check_deps.py --json catalog/fixtures/deps/undeclared.py`.
`opa_gate.py deps <this> --expect denied:D1` must hold."""


def uses_an_undeclared_dependency():
    import el_openglo_w75_undeclared_dep  # noqa: F401
    return el_openglo_w75_undeclared_dep
