# SPDX-License-Identifier: Apache-2.0
# Stub: BoundsPen as make_glyph_ink uses it (W255).
from collections.abc import Mapping
from typing import Protocol

class _Drawable(Protocol):
    def draw(self, pen: BoundsPen) -> None: ...

class BoundsPen:
    bounds: tuple[float, float, float, float] | None
    def __init__(self, glyphSet: Mapping[str, _Drawable] | None) -> None: ...
