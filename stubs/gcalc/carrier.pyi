# SPDX-License-Identifier: Apache-2.0
# Stub: the two carrier reads scripts/check_relations.py makes (gcalc/carrier.py:210, :467) (W255).
from collections.abc import Iterator

# A term of the g-calculus is a tagged tuple (("leaf", name), ("lift", term), ("part", a, b), ...).
type Term = tuple[object, ...]

def parts_of(t: Term) -> tuple[Term, ...]: ...
def support(t: Term) -> Iterator[str]: ...
