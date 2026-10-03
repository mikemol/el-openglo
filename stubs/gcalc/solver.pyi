# SPDX-License-Identifier: Apache-2.0
# Stub: the solver names this tree calls (signatures read from gcalc/solver.py, 2026-10-03) (W255).
from collections.abc import Iterable, Iterator, Mapping, Sequence
from fractions import Fraction

from gcalc.carrier import Term

type Edge = tuple[str, str]

class Netlist(Mapping[Edge, Term]):
    """A key-sorted carrier of (u, v) -> admittance term (solver.netlist)."""
    def __getitem__(self, key: Edge) -> Term: ...
    def __iter__(self) -> Iterator[Edge]: ...
    def __len__(self) -> int: ...

class Cycle:
    """One fundamental cycle: a key-sorted run of (edge, sign) pairs."""
    def __iter__(self) -> Iterator[tuple[Edge, int]]: ...

class Section:
    """What frontier_solve returns first: read only through total_cost and verdict."""

class Frozen:
    nodes: list[str]
    edges: Netlist
    cost: list[tuple[str, int]]
    gauge: list[str]
    def step(self, x: str) -> Frozen: ...

def netlist(edges: Mapping[Edge, str] | Iterable[tuple[Edge, str]]) -> Netlist: ...
def cycle_basis(nodes: Sequence[str], edges: Mapping[Edge, object]) -> list[Cycle]: ...
def freeze(
    nodes: Sequence[str], edges: Netlist, keep: tuple[str, ...] = ()
) -> Frozen: ...
def min_degree(fz: Frozen) -> str | None: ...
def laplacian(
    nodes: Sequence[str], edges: Netlist, env: Mapping[str, Fraction]
) -> tuple[list[list[Fraction]], Mapping[str, int]]: ...
def r_eff(
    nodes: Sequence[str], edges: Netlist, env: Mapping[str, Fraction], s: str, t: str
) -> Fraction: ...
def frontier_solve(
    nodes: Sequence[str],
    edges: Netlist,
    order: Iterable[str],
    keep: tuple[str, ...] = (),
) -> tuple[Section, Netlist, list[str]]: ...
def total_cost(sec: Section) -> int: ...
def verdict(sec: Section) -> str: ...
