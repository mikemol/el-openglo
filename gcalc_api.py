# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""gcalc_api — the ONE place this tree reaches the gcalculus sibling (W485).

⚑ WHY ONE PLACE. gcalculus (~/github/gcalculus) is LOCATED, not vendored (pyproject records it as
deliberately undeclared). On 2026-10-09 it split `gcalc/solver.py` into a PACKAGE OF NAMESPACES
(gcalculus W51: "import each name from the module that defines it ... nothing is re-exported"),
and four checks here (check_nodal, check_palette_graph, check_relations, check_netlist_render) read
`gcalc.solver.netlist`, `.freeze`, `.cycle_basis` off the old flat module: the commit gate went red
with `AttributeError: module 'gcalc.solver' has no attribute 'freeze'`. Each caller had its own copy
of the locate-and-import dance, so the drift surfaced four times. Now a sibling move is ONE edit
here, and `check_gcalc_api` fails by NAME when this module asks for something the sibling does not
define.

    import gcalc_api as S
    if S.AVAILABLE: S.netlist(...), S.freeze(...), S.cycle_basis(...)

AVAILABLE is False when the sibling is absent: a fact about the machine, so a caller SKIPS (counted,
printed) and never reads that as the artifact failing. NOT CONFIRMED IS NOT FAILED.

WEAKNESS: AVAILABLE folds any ImportError (an absent sibling, or a name the sibling moved) into
False, so a MOVED name reads as a SKIP here; scripts/check_gcalc_api.py is what tells the two apart
(it imports each name and names the one that is gone).
"""

import os
import sys

GCALC = os.path.expanduser("~/github/gcalculus")

AVAILABLE = False
if os.path.isdir(GCALC) and GCALC not in sys.path:
    sys.path.insert(0, GCALC)
try:
    from gcalc.carrier import parts_of, support
    from gcalc.solver.driver import (
        freeze,
        frontier_solve,
        min_degree,
        total_cost,
        verdict,
    )
    from gcalc.solver.laplacian import laplacian, r_eff
    from gcalc.solver.mesh import cycle_basis
    from gcalc.solver.netlist import netlist

    AVAILABLE = True
except ImportError:
    AVAILABLE = False

# the names this tree reads, each with the sibling module that defines it: the declaration
# check_gcalc_api verifies against the sibling itself
NAMES = {
    "parts_of": "gcalc.carrier",
    "support": "gcalc.carrier",
    "frontier_solve": "gcalc.solver.driver",
    "freeze": "gcalc.solver.driver",
    "min_degree": "gcalc.solver.driver",
    "total_cost": "gcalc.solver.driver",
    "verdict": "gcalc.solver.driver",
    "laplacian": "gcalc.solver.laplacian",
    "r_eff": "gcalc.solver.laplacian",
    "cycle_basis": "gcalc.solver.mesh",
    "netlist": "gcalc.solver.netlist",
}

__all__ = [
    "AVAILABLE",
    "GCALC",
    "NAMES",
    "cycle_basis",
    "freeze",
    "frontier_solve",
    "laplacian",
    "min_degree",
    "netlist",
    "parts_of",
    "r_eff",
    "support",
    "total_cost",
    "verdict",
]
