# SPDX-License-Identifier: Apache-2.0
# Stub: the pens this tree records outlines with (W255). `value` is the recorded
# (operator, operands) list; operands are points, a qCurveTo may also carry a None
# (an all-off-curve contour), which no caller here reaches.
from collections.abc import Mapping
from typing import Protocol

type Point = tuple[float, float]

class _Drawable(Protocol):
    def draw(self, pen: RecordingPen) -> None: ...

class RecordingPen:
    value: list[tuple[str, tuple[Point, ...]]]
    def __init__(self) -> None: ...

class DecomposingRecordingPen(RecordingPen):
    def __init__(self, glyphSet: Mapping[str, _Drawable]) -> None: ...
