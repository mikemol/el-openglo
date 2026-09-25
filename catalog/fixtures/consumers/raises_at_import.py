"""W75 negative fixture for policy/consumers.rego: a module whose TOP LEVEL fails
when imported — the defect the gate exists for (cvd_gate's attributes absent,
make_palette broken, nothing red because every file still byte-compiled).
Planted by `check_consumers.py --json catalog/fixtures/consumers/raises_at_import.py`;
`opa_gate.py consumers <this> --expect denied:I2` must hold."""

raise AttributeError("module 'cvd_gate' has no attribute 'stretch_lit' (W75 fixture)")
