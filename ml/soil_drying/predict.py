"""Load the exported model and predict hours until a bed needs water.

    from soil_drying.predict import SoilDryingModel
    model = SoilDryingModel.load()
    hours = model.predict(moisture_history, air_temp_c=24, air_humidity_pct=55,
                          hour=18, forecast_rain_24h=0.0, forecast_et0_24h=4.5)

`moisture_history` is the last 25 hourly soil_moisture_pct readings, oldest first
(GET /api/readings?node=irrigation-1&metric=soil_moisture_pct&from=<now-25h>).
"""
from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from .features import FEATURES, HORIZON_H, feature_row

MODELS = Path(__file__).resolve().parent.parent / "models"


class SoilDryingModel:
    def __init__(self, estimator, meta: dict):
        self.estimator = estimator
        self.meta = meta

    @classmethod
    def load(cls, folder: Path = MODELS) -> "SoilDryingModel":
        meta = json.loads((Path(folder) / "soil_drying.json").read_text())
        return cls(joblib.load(Path(folder) / "soil_drying.joblib"), meta)

    def predict_row(self, row: dict) -> float:
        x = pd.DataFrame([row], columns=FEATURES)
        return float(np.clip(self.estimator.predict(x)[0], 0, HORIZON_H))

    def predict(self, moisture_history, air_temp_c: float, air_humidity_pct: float, hour: int,
                forecast_rain_24h: float, forecast_et0_24h: float) -> float:
        history = np.asarray(moisture_history, dtype=float)
        if len(history) < 25:
            raise ValueError("need the last 25 hourly moisture readings")
        threshold = self.meta.get("threshold", 25.0)
        return self.predict_row(feature_row(history[-25:], air_temp_c, air_humidity_pct, hour,
                                            forecast_rain_24h, forecast_et0_24h, threshold))
