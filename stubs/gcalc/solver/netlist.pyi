# SPDX-License-Identifier: Apache-2.0
# Stub: gcalc.solver.netlist as this tree calls it (signature read from the sibling, 2026-10-10) (W485).
from collections.abc import Iterable, Iterator, Mapping

from gcalc.carrier import Term

type Edge = tuple[str, str]

class Netlist(Mapping[Edge, Term]):
    """A key-sorted carrier of (u, v) -> admittance term."""
    def __getitem__(self, key: Edge) -> Term: ...
    def __iter__(self) -> Iterator[Edge]: ...
    def __len__(self) -> int: ...

def netlist(edges: Mapping[Edge, str] | Iterable[tuple[Edge, str]]) -> Netlist: ...
