# SPDX-License-Identifier: Apache-2.0
# Stub: only the scipy.ndimage names this tree uses (W255); extend when mypy names a missing one.
import numpy as np
import numpy.typing as npt

def label(
    input: npt.ArrayLike,
    structure: npt.ArrayLike | None = None,
) -> tuple[npt.NDArray[np.int32], int]: ...
