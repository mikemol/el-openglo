# SPDX-License-Identifier: Apache-2.0
# Stub for the one colorspacious call this tree makes (cvd_gate.py): declared, not ignored (W255).
import numpy as np
import numpy.typing as npt

def cspace_convert(
    arr: npt.ArrayLike,
    start: str | dict[str, str | int],
    end: str | dict[str, str | int],
) -> npt.NDArray[np.float64]: ...
