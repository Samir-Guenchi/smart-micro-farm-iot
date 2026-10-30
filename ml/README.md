# Machine learning

## Soil-drying prediction (`soil_drying/`, `soil_drying.ipynb`)

Predicts **how many hours until a bed's soil moisture falls below the watering
threshold** (25 %), from the last 25 hourly moisture readings, air temperature
and humidity, and the 24-hour forecast (rain, evapotranspiration).

The farm has no season of its own data yet, so the model is trained on a
simulator: randomised beds (soil, root depth, crop factor) under generated
Baltic and Mediterranean summers, with sensor noise and an imperfect forecast.
Retrain on real readings once a season exists.

### Results on simulated beds the model has never seen

| | Mean error, all | Mean error, beds needing water within 24 h |
|---|---|---|
| Gradient-boosted model | 9.2 h | 5.7 h |
| Straight-line trend (baseline) | 21.4 h | 23.7 h |

Water used over 150 days, 4 beds, same weather and forecasts for each policy:

| Policy | Temperate | vs schedule | Mediterranean | vs schedule |
|---|---|---|---|---|
| Water every evening by habit | 24,000 L | | 24,000 L | |
| Threshold rule (firmware today) | 16,120 L | −33 % | 20,600 L | −14 % |
| Threshold + skip when rain forecast | 16,040 L | −33 % | 20,520 L | −15 % |
| Model, checked once a day at 18:00 | 16,080 L | −33 % | 20,640 L | −14 % |

No policy let any bed fall below the 20 % stress line.

**Honest reading:** watering by sensor saves a lot compared with watering by
habit, but in this simulator the model saves almost nothing compared with the
threshold rule (+0.2 % / −0.2 %), because small doses keep the soil well below
field capacity and rain is stored, not wasted. The model's real value today is
**prediction**: the farm agent can say "bed 2 will need water in about 9 hours"
and plan one evening run. Savings over the threshold rule have to be measured
again on the farm's own data. The notebook explains the details and next steps.

### Use the exported model

```python
from soil_drying.predict import SoilDryingModel

model = SoilDryingModel.load()          # models/soil_drying.joblib + .json
hours = model.predict(
    moisture_history,                   # last 25 hourly soil_moisture_pct readings, oldest first
    air_temp_c=24, air_humidity_pct=55, hour=18,
    forecast_rain_24h=0.0, forecast_et0_24h=4.5,
)
```

`models/soil_drying.json` records the features, threshold, metrics and the
scikit-learn version the model was saved with; load it with the same major
version.

### Run, retrain, test

```bash
cd ml
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
jupyter notebook soil_drying.ipynb       # or: jupyter nbconvert --to notebook --execute --inplace soil_drying.ipynb
pytest
```

Running the notebook end to end regenerates the data, retrains, re-runs the
policy comparison and re-exports the model (deterministic seeds).
