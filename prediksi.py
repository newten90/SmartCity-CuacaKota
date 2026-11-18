"""Estimasi suhu rata-rata harian, dalam kalender WIB."""
from datetime import timedelta
import numpy as np
import pandas as pd

from analisis import TEMP

HORIZON = 7
MIN_HOURS = 18


def calendar_features(dates):
    index = pd.DatetimeIndex(dates)
    phase = 2 * np.pi * (index.dayofyear - 1) / np.where(index.is_leap_year, 366, 365)
    return np.column_stack([np.ones(len(index)), np.sin(phase), np.cos(phase)])


def fit(series):
    x = calendar_features(series.index)
    weights = np.linalg.lstsq(x, series, rcond=None)[0]
    residual = series - x @ weights
    # Reindex mempertahankan jarak kalender saat ada hari yang hilang.
    residual = residual.asfreq("D")
    persistence = residual.autocorr(lag=1)
    return weights, float(np.clip(persistence, 0, 1)) if np.isfinite(persistence) else 0.0


def forecast(model, today, yesterday_temp=None):
    weights, persistence = model
    dates = pd.date_range(pd.Timestamp(today) + timedelta(days=1), periods=HORIZON)
    values = calendar_features(dates) @ weights
    if yesterday_temp is not None:
        yesterday = pd.Timestamp(today) - timedelta(days=1)
        typical = (calendar_features([yesterday]) @ weights).item()
        ages = np.arange(2, HORIZON + 2)
        values += (yesterday_temp - typical) * persistence ** ages
    return pd.Series(values, index=dates)


def train(data):
    models = {}
    for city, group in data.groupby("kota"):
        daily = group.groupby("tanggal")[TEMP].agg(["mean", "count"])
        series = daily.loc[daily["count"] == 24, "mean"].copy()
        series.index = pd.to_datetime(series.index)
        evaluation_model = fit(series.loc[:"2025-09-30"])
        errors = {False: [], True: []}
        for issue in pd.date_range("2025-10-01", pd.Timestamp("2025-12-31") - timedelta(days=HORIZON)):
            yesterday = series.get(issue - timedelta(days=1))
            for adjusted in errors:
                if adjusted and pd.isna(yesterday):
                    continue
                estimates = forecast(evaluation_model, issue, yesterday if adjusted else None)
                errors[adjusted].extend((estimates - series.reindex(estimates.index)).abs().dropna())
        models[city] = fit(series), {mode: float(np.mean(err)) for mode, err in errors.items()}
    return models
