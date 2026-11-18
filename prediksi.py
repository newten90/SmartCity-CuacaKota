"""Prediksi suhu satu jam setelah waktu pengukuran, per kota."""
import numpy as np
import pandas as pd

from analisis import TEMP, RH


def features(temp, humidity, hour):
    phase = 2 * np.pi * hour / 24
    return np.column_stack((np.ones_like(temp), temp, humidity, np.sin(phase), np.cos(phase)))


def train(data):
    models = {}
    for city, group in data.groupby("kota"):
        frame = group.set_index(pd.to_datetime(group.waktu)).sort_index()
        frame["target"] = frame[TEMP].shift(-1, freq="h")
        frame = frame.dropna(subset=[TEMP, RH, "target"])
        x = features(frame[TEMP], frame[RH], frame.index.hour)
        y = frame.target.to_numpy()
        # Kedua waktu dalam pasangan latih harus berada sebelum awal Oktober.
        cutoff = pd.Timestamp("2025-10-01")
        training = frame.index + pd.Timedelta(hours=1) < cutoff
        testing = frame.index >= cutoff
        weights = np.linalg.lstsq(x[training], y[training], rcond=None)[0]
        mae = np.abs(x[testing] @ weights - y[testing]).mean()
        baseline = np.abs(frame[TEMP].to_numpy()[testing] - y[testing]).mean()
        models[city] = weights, mae, baseline
    return models


def forecast(weights, temp, humidity, stamp):
    hour = stamp.hour + stamp.minute / 60
    return (features(temp, humidity, hour) @ weights).item()
