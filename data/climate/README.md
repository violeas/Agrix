# Climate data interface and sources

The provider boundary is declared in `interface.py`. The live adapters are in `services/monsoon/providers.py`; they can be replaced by station, IMD, state-agency or private feeds without changing Flask routes. Every provider returns source and availability metadata. Missing values remain `null`/unavailable.

## Connected real data

- **Weather ensemble:** Open-Meteo GFS Seamless ensemble API, daily precipitation by ensemble member, requested for 30 days at the selected coordinate. The application reports raw ensemble-member frequencies for measurable rain, a five-day dry run and at least 64.5 mm in a day. These are uncalibrated, model-grid probabilities, not AgriShield ML predictions.
- **Recent rainfall:** Open-Meteo Historical Weather API reanalysis for the selected point. Recent values can be delayed and are grid estimates rather than gauge readings.
- **ENSO:** NOAA Climate Prediction Center RONI text index; the index period/date is shown.
- **IOD:** NOAA Physical Sciences Laboratory DMI HadISST monthly CSV; the last available month is shown and can be dated.
- **MJO:** Australian Bureau of Meteorology RMM daily text feed; phase, amplitude and observation date are shown.
- **Location search:** Open-Meteo Geocoding API. Reverse address lookup uses OpenStreetMap Nominatim. The app shows only returned address fields; block and panchayat are not inferred.
- **Map:** OpenStreetMap map view centered on the selected coordinate. No fabricated district or village polygons are drawn.

The external sources above are fetched at request time, cached in process for the current date/coordinate, and have provider timeouts. Public endpoints can change, rate-limit, or be unavailable. Review each source's current license and acceptable-use terms before public/commercial deployment.

## Not connected / not derived

- No administrative GeoJSON is bundled. `boundaries.py` can resolve a point against a configured authoritative GeoJSON, but never aggregates weather-grid output into area predictions.
- IMD official monsoon onset/withdrawal and false-onset labels, local station observations, soil moisture, and local climatological normals are not bundled.
- Validated relationships from ENSO/IOD/MJO to a district forecast. Driver cards are contextual observations only.
- A trained AgriShield model or calibrated probabilities. The model pipeline is data-ready and only exposes local model output after chronological held-out checks; no current project-local observations are assumed.

## Canonical observation fields

Daily CSV ingestion uses `date`, `location_id`, `rainfall_mm`, `source`; optional fields are `latitude`, `longitude`, `temperature_c`, `humidity_percent`, `wind_kmh`, `pressure_hpa`, `enso_index`, `iod_index`, `mjo_rmm1`, `mjo_rmm2`, `mjo_phase`, `mjo_amplitude`, `normal_rainfall_mm`, `onset_event`, and `false_onset_event`. Units and event-label definitions must be consistent. Missing values remain missing. The importer rejects mixed location IDs.

Import observations with `python -m data.climate.ingest --input path.csv --location-id district:NAME:STATE --source station`. Train one location with `python -m models.monsoon.training --location-id district:NAME:STATE`. Use multi-year daily observations, official event labels for onset and false onset, and local normals before interpreting those targets.

Crop calendars can be imported from CSV using `python -m data.climate.crop_calendar --input calendars.csv`. Required columns: `location_id,crop_name,source`; optional columns: `sowing_start,sowing_end` (MM-DD), `water_requirement_mm_day`, `lifecycle_stages_json` (for example `[ {"day":0,"stage":"Establishment"}, {"day":20,"stage":"Vegetative"} ]`), and `version`. No crop-calendar sample data is bundled.

To match returned GPS coordinates against trusted administrative polygons, set `AGRISHIELD_BOUNDARY_GEOJSON` to an authoritative GeoJSON Feature/FeatureCollection. Properties are read from state/district/block/mandal/panchayat or village fields and available IDs. This only enriches location labels; risk values remain weather-grid guidance unless area observations, area-specific model training and aggregation validation are added.
