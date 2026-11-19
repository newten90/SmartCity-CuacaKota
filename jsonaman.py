"""Mengubah hasil Pandas/NumPy menjadi nilai JSON biasa. NaN, NaT, dan tak hingga menjadi null."""
from datetime import date, datetime
import math

import numpy as np
import pandas as pd


def bersih(value):
    if isinstance(value, dict):
        return {str(key): bersih(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [bersih(item) for item in value]
    if isinstance(value, pd.DataFrame):
        return bersih(value.to_dict("records"))
    if isinstance(value, pd.Series):
        return bersih(value.to_dict())
    if value is None or value is pd.NaT:
        return None
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value
