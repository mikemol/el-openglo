# SPDX-License-Identifier: Apache-2.0
# Stub for cairosvg.svg2png as this tree calls it (signature read from the installed package): declared, not ignored (W255).
from os import PathLike
from typing import IO

def svg2png(
    bytestring: bytes | str | None = None,
    *,
    file_obj: IO[bytes] | None = None,
    url: str | None = None,
    dpi: float = 96,
    parent_width: float | None = None,
    parent_height: float | None = None,
    scale: float = 1,
    unsafe: bool = False,
    background_color: str | None = None,
    negate_colors: bool = False,
    invert_images: bool = False,
    write_to: str | PathLike[str] | IO[bytes] | None = None,
    output_width: float | None = None,
    output_height: float | None = None,
) -> bytes | None: ...
