# AgriShield Monsoon & Crop Intelligence

AgriShield is a React + Flask + SQLite agricultural decision-support application. Monsoon Intelligence is the main screen and connects weather guidance with saved crop profiles and lifecycle stages. Existing crop health, image upload, diagnosis, scan history, recommendations and languages remain available.

Forecasts are planning information, not official warnings or guaranteed agricultural instructions. The provider forecast is gridded and its ensemble-member frequencies are raw, uncalibrated signals. AgriShield does not claim local forecast skill until a local model has been trained and evaluated on held-out historical observations.

## Current data and limitations

**Live provider adapters:** Open-Meteo GFS Seamless ensemble rainfall, Open-Meteo gridded historical rainfall reanalysis, NOAA CPC RONI, NOAA PSL DMI, Australian Bureau of Meteorology RMM, Open-Meteo place search, OpenStreetMap reverse geocoding and map tiles. Provider results are fetched at request time and may be unavailable or rate-limited.

**Imported local data:** None is bundled. Climate observations, official onset/false-onset labels, local rainfall normals, crop calendars and authoritative boundary files are data-ready import interfaces. No sample rows are loaded into the production SQLite database.

**Unavailable until supplied and validated:** AgriShield trained local probabilities and metrics; official local onset and false-onset probabilities; historical local rainfall normals/anomalies; crop-specific water and sowing-window suitability; panchayat/block weather aggregation; soil moisture. ENSO/IOD/MJO are shown as dated index context and are not currently applied as local forecast adjustments.

The map marks the selected provider grid point. Optional boundary matching may display an authoritative administrative label when a GeoJSON is configured, but does not turn that point into an area forecast.

## Architecture

```text
React / Vite (src/)
  ├── Monsoon Intelligence, farmer crop state and timeline
  └── same-origin /api requests (Vite proxies to Flask during development)
          ↓
Flask API (app.py)
  ├── SQLite and safe additive migrations (database.py)
  ├── live weather and climate adapters (services/monsoon/)
  ├── transparent decision/advisory rules (services/monsoon/decision.py)
  └── crop lifecycle, image diagnosis, health history
          ↓
Climate data interface and importers (data/climate/)
  └── leakage-aware features, chronological baseline and evaluation (models/monsoon/)
```

SQLite retains the existing crop, scan, diagnosis and settings tables. Additive migrations add crop location/field metadata, canonical climate observations, crop calendar rules, model runs/metrics and in-app monsoon alerts. Crop archive is a reversible status change and preserves scans.

## Live provider inputs

| Data | Source | Interpretation |
| --- | --- | --- |
| 30-day precipitation ensemble | Open-Meteo Ensemble API, GFS Seamless | Grid rainfall and raw member frequencies. Not locally calibrated. |
| Recent rainfall | Open-Meteo Historical Weather API | Delayed reanalysis grid values, not rain-gauge observations. |
| ENSO | NOAA CPC RONI | Global climate-index context. |
| IOD | NOAA PSL DMI | Monthly climate-index context. |
| MJO | Australian Bureau of Meteorology RMM | Phase/amplitude context with source date. |
| Location search | Open-Meteo Geocoding API | Shows only place/admin values returned by geocoder. |
| Reverse geocoding and basemap | OpenStreetMap Nominatim and map tiles | Point labels/map only; no default location or fabricated boundaries. |

Review public providers' current terms before commercial deployment. Configure `AGRISHIELD_USER_AGENT`, `AGRISHIELD_CONTACT` and timeouts in `.env` as needed.

## Historical data schema and import

Daily climate CSV requires `date`, `rainfall_mm`, `location_id` (or pass `--location-id`) and `source` (or pass `--source`). Supported optional columns:

```text
latitude,longitude,temperature_c,humidity_percent,wind_kmh,pressure_hpa,
enso_index,iod_index,mjo_rmm1,mjo_rmm2,mjo_phase,mjo_amplitude,
normal_rainfall_mm,onset_event,false_onset_event
```

Missing values are not filled with invented observations. Spatial alignment is exact by `location_id`; climate indices only carry forward from earlier dates within the configured maximum age. For production data retain units, quality flags, station/grid identity, spatial resolution and documented event definitions.

Import one location per CSV:

```powershell
python -m data.climate.ingest --input path\to\observations.csv --location-id district:NAME:STATE --source station
```

Train and save a versioned, location-specific baseline:

```powershell
python -m models.monsoon.training --location-id district:NAME:STATE
```

The pipeline creates rolling rainfall, dry-run, intensity, climate-index lag and seasonal features. It fits deterministic logistic-regression event models for 7/14/21/30 day onset, false-onset, dry-spell and heavy-rain targets plus a linear rainfall-anomaly baseline when normals are supplied. Splits are chronological with horizon-sized target gaps; scaling is fitted on training rows. Onset/false-onset require official event labels. A target without sufficient samples or both classes remains unavailable. Metrics are calculated on held-out dates; raw logistic scores are not probability-calibrated. Do not use the included test fixture as training evidence.

Crop calendars accept CSV with required `location_id,crop_name,source` and optional `sowing_start,sowing_end` (`MM-DD`), `water_requirement_mm_day`, `lifecycle_stages_json` and `version`. Lifecycle JSON example: `[{"day":0,"stage":"Establishment"},{"day":20,"stage":"Vegetative"}]`.

```powershell
python -m data.climate.crop_calendar --input path\to\crop-calendars.csv
```

No crop-calendar samples are bundled. Imported local lifecycle data is used only for the matching crop and location; otherwise configured crop-stage estimates say they are not locally calibrated.

For authoritative administrative boundary lookup, set `AGRISHIELD_BOUNDARY_GEOJSON` to an official/local GeoJSON Feature or FeatureCollection. Supported geometry is Polygon/MultiPolygon. `data/climate/boundaries.py` matches coordinates to source properties such as district, block/mandal, panchayat/village and available boundary IDs. Boundary matching is for location labeling; area aggregation and panchayat forecasts are not implemented.

## Local setup and run

Prerequisites: Python 3.10+, Node.js 20.19+ (or 22.12+) and dependencies installed once:

```powershell
python -m pip install -r requirements.txt
pnpm install
```

Open two PowerShell terminals at the project folder.

Terminal 1, Flask backend:

```powershell
python app.py
```

Terminal 2, React/Vite frontend:

```powershell
pnpm run dev
```

Then open [http://localhost:5173](http://localhost:5173). Vite proxies `/api` and `/uploads` to Flask at port 8000. The SQLite schema is initialized on backend startup. Select a location explicitly; GPS permission is requested only when the user presses the GPS button.

If Windows does not recognize `python` or `pnpm`, install Python/Node.js and reopen PowerShell, or use the full executable path for those commands. Both servers must remain running while the site is open.

## Checks

```powershell
python -m compileall -q app.py database.py services models data
python -m unittest discover -s tests -v
pnpm run test:frontend
pnpm run build
```

Backend/API tests use temporary databases. A trained-model test uses a deterministic fixture only to verify the pipeline; it is not evidence of real accuracy. No true local model metrics exist until real historical observations/event labels are imported and the training command completes for a location.

## Main API routes

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET/POST | `/api/location` | Read/save explicit selected location. |
| GET | `/api/location/search`, `/api/location/reverse` | Manual search and GPS coordinate lookup. |
| GET | `/api/monsoon/forecast` | Provider outlook and separately labeled validated local model output. |
| GET | `/api/monsoon/risk-map` | Selected grid-point risk values and boundary-match metadata. |
| GET | `/api/monsoon/sowing-window` | Transparent suitability status and missing input reasons. |
| GET | `/api/monsoon/advisory` | Legacy advisory strings plus structured crop-aware details. |
| GET | `/api/monsoon/alerts` | Persisted in-app provider/model signal alerts. |
| GET | `/api/monsoon/model-performance` | Stored held-out metrics without exposing model weights. |
| GET/POST/PUT/DELETE | `/api/crops` and `/api/crops/<id>` | Persist, update and archive crop profiles. |
| GET | `/api/crop-timeline?crop_id=...` | Saved crop state, lifecycle and image scan history. |

Alerts are in-app only. SMS/WhatsApp delivery and outbound messaging are not configured.
