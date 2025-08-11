import numpy as np


def _to_float(s):
    """Convenience method to convert string to float."""
    if isinstance(s, str):
        return float(np.char.replace(np.char.replace(s, " ", ""), ",", "."))
    else:
        return s
