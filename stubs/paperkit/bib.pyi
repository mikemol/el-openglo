# SPDX-License-Identifier: Apache-2.0
# Stub: paperkit.bib.parse (signature and record shape read from paperkit/bib.py): {key: {field: scalar or list, _src, _type}}.
from pathlib import Path

def parse(
    path: Path, consumer_fields: tuple[str, ...] = ()
) -> dict[str, dict[str, str | list[str]]]: ...
