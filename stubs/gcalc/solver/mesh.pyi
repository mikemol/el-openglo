# SPDX-License-Identifier: Apache-2.0
# Stub: gcalc.solver.mesh as this tree calls it (signature read from the sibling, 2026-10-10) (W485).
from collections.abc import Iterator, Mapping, Sequence

from gcalc.solver.netlist import Edge

class Cycle:
    """One fundamental cycle: a key-sorted run of (edge, sign) pairs."""
    def __iter__(self) -> Iterator[tuple[Edge, int]]: ...

def cycle_basis(nodes: Sequence[str], edges: Mapping[Edge, object]) -> list[Cycle]: ...
