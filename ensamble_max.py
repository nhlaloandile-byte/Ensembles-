import os
from datetime import datetime, timezone

import pandas as pd
import requests

CITIES = {
    "Paris": (48.85, 2.35),
    "Milan": (45.46, 9.19),
    "London": (51.51, -0.13),
}
MODELS = ["icon_global", "icon_eu", "icon_d2", "ecmwf_ifs025"]
OUT = "ensemble_max.csv"


def daily_stats(lat, lon, model):
    r = requests.get(
        "https://ensemble-api.open-meteo.com/v1/ensemble",
        params={
            "latitude": lat,
            "longitude": lon,
            "hourly": "temperature_2m",
            "models": model,
            "timezone": "auto",
            "forecast_days": 3,
        },
        timeout=60,
    )
    r.raise_for_status()
    df = pd.DataFrame(r.json()["hourly"]).set_index("time")
    df.index = pd.to_datetime(df.index)
    members = df.filter(like="temperature_2m")
    per_member = members.resample("D").max()  # each member's daily high
    out = pd.DataFrame(
        {
            "max_member": per_member.max(axis=1),
            "mean": per_member.mean(axis=1),
            "min_member": per_member.min(axis=1),
        }
    )
    out.index.name = "date"
    return out.reset_index()


rows = []
fetched = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
for city, (lat, lon) in CITIES.items():
    for model in MODELS:
        try:
            d = daily_stats(lat, lon, model)
        except Exception as e:  # e.g. ICON-D2 doesn't cover every city
            print(f"Skipped {city}/{model}: {e}")
            continue
        d.insert(0, "model", model)
        d.insert(0, "city", city)
        d.insert(0, "fetched_utc", fetched)
        rows.append(d)

if rows:
    result = pd.concat(rows).round(1)
    result.to_csv(OUT, mode="a", header=not os.path.exists(OUT), index=False)
    print(result.to_string(index=False))
