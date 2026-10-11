# SPDX-License-Identifier: Apache-2.0
# Stub: gcalc.solver.laplacian as this tree calls it (signatures read from the sibling, 2026-10-10) (W485).
from collections.abc import Mapping, Sequence
from fractions import Fraction

from gcalc.solver.netlist import Netlist

def laplacian(
    nodes: Sequence[str], edges: Netlist, env: Mapping[str, Fraction]
) -> tuple[list[list[Fraction]], Mapping[str, int]]: ...
def r_eff(
    nodes: Sequence[str], edges: Netlist, env: Mapping[str, Fraction], s: str, t: str
) -> Fraction: ...
