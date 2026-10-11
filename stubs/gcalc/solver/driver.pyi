# SPDX-License-Identifier: Apache-2.0
# Stub: gcalc.solver.driver as this tree calls it (signatures read from the sibling, 2026-10-10) (W485).
from collections.abc import Iterable, Sequence

from gcalc.solver.netlist import Netlist

class Section:
    """What frontier_solve returns first: read only through total_cost and verdict."""

class Frozen:
    nodes: list[str]
    edges: Netlist
    cost: list[tuple[str, int]]
    gauge: list[str]
    def step(self, x: str) -> Frozen: ...

def freeze(
    nodes: Sequence[str], edges: Netlist, keep: tuple[str, ...] = ()
) -> Frozen: ...
def min_degree(fz: Frozen) -> str | None: ...
def frontier_solve(
    nodes: Sequence[str],
    edges: Netlist,
    order: Iterable[str],
    keep: tuple[str, ...] = (),
) -> tuple[Section, Netlist, list[str]]: ...
def total_cost(sec: Section) -> int: ...
def verdict(sec: Section) -> str: ...
