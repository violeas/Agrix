from io import BytesIO
from datetime import date, timedelta
import tempfile
import unittest
import json
from pathlib import Path
from unittest.mock import patch
from PIL import Image

import app as app_module
import database
from models.monsoon.baseline import load_historical_csv, predict, run_baseline_csv, time_series_features, train_baseline
from models.monsoon.evaluation import brier_score, regression_metrics
from models.monsoon.evaluation import binary_classification_metrics, reliability_bins
from models.monsoon.training import build_samples, train_location_model, forecast_with_model_run
from data.climate.ingest import load_csv, ingest_csv
from data.climate.crop_calendar import ingest_csv as ingest_crop_calendar_csv
from data.climate.boundaries import resolve_boundary
from data.climate.preprocessing import normalize_observation, rolling_features, temporal_align
from services.lifecycle import estimate_growth_stage
from services.monsoon.forecast import _ensemble_members, _max_dry_run, sowing_decision
from services.monsoon.decision import explain_forecast


def test_png():
    image = Image.new("RGB", (160, 160), (80, 140, 60))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


class MonsoonModelTests(unittest.TestCase):
    def setUp(self):
        self.original_db_path = database.DB_PATH
        self.tmp = tempfile.TemporaryDirectory()
        database.DB_PATH = Path(self.tmp.name) / "model-test.db"
        database.init_db()
        self.rows = [{"date": f"2026-01-{day:02d}", "rainfall_mm": 0 if day % 3 else 4,
                      "temperature_c": 28, "humidity_percent": 65, "enso_index": .2,
                      "iod_index": -.1, "mjo_phase": 4, "wind_kmh": 8}
                     for day in range(1, 61)]

    def tearDown(self):
        database.DB_PATH = self.original_db_path
        self.tmp.cleanup()

    def test_real_input_baseline_outputs_requested_horizons_and_bounded_probabilities(self):
        model = train_baseline(self.rows)
        forecast = predict(model)
        self.assertEqual([item["days"] for item in forecast], [7, 14, 21, 30])
        self.assertTrue(all(0 <= item["rainfall_probability"] <= 1 for item in forecast))
        self.assertEqual(model["daily_samples"], 60)

    def test_csv_loader_runs_the_historical_baseline_without_fabricating_optional_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "rainfall.csv"
            start = date(2025, 1, 1)
            rows = ["date,rainfall_mm,temperature_c"]
            rows.extend(f"{start + timedelta(days=i)},{4 if i % 4 == 0 else 0}," for i in range(35))
            path.write_text("\n".join(rows), encoding="utf-8")
            loaded = load_historical_csv(path)
            result = run_baseline_csv(path)
        self.assertIsNone(loaded[0]["temperature_c"])
        self.assertEqual(result["model"]["daily_samples"], 35)
        self.assertEqual([item["days"] for item in result["forecast"]], [7, 14, 21, 30])

    def test_time_series_features_and_metrics(self):
        features = time_series_features(self.rows)
        self.assertEqual(len(features), 60)
        self.assertEqual(features[1]["temperature_c"], 28)
        self.assertEqual(regression_metrics([1, 3], [2, 2])["mae"], 1)
        self.assertAlmostEqual(brier_score([0, 1], [.2, .8])["brier"], .04)
        metrics = binary_classification_metrics([0, 1, 1, 0], [.1, .8, .4, .6])
        self.assertAlmostEqual(metrics["f1"], .5)
        self.assertAlmostEqual(metrics["roc_auc"], .75)
        self.assertEqual(len(reliability_bins([0, 1], [.1, .8])), 10)

    def test_preprocessing_does_not_fill_missing_or_borrow_future_climate_values(self):
        daily = [{"date": "2026-01-01", "location_id": "district:a", "rainfall_mm": 1.0},
                 {"date": "2026-01-02", "location_id": "district:a", "rainfall_mm": None},
                 {"date": "2026-01-03", "location_id": "district:a", "rainfall_mm": 0.0}]
        aligned = temporal_align(daily, [{"date": "2026-01-02", "enso_index": .4}], ["enso_index"])
        featured = rolling_features(aligned)
        self.assertIsNone(aligned[0]["enso_index"])
        self.assertIsNone(featured[1]["rolling_rain_3d_mm"])
        self.assertEqual(aligned[2]["enso_index"], .4)
        row = normalize_observation({"date": "2026-01-01", "rainfall_mm": "", "temperature_c": "20"}, "district:a", "test")
        self.assertIsNone(row["rainfall_mm"])
        self.assertEqual(row["temperature_c"], 20.0)

    def test_imported_crop_calendar_drives_lifecycle_only_for_its_explicit_location(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "calendar.csv"
            path.write_text('location_id,crop_name,source,sowing_start,sowing_end,water_requirement_mm_day,lifecycle_stages_json,version\n'
                            'district:test:state,Maize,State Agriculture Dept,06-01,07-15,4.2,"[{""day"":0,""stage"":""Emergence""},{""day"":20,""stage"":""Vegetative""}]",v1\n', encoding="utf-8")
            self.assertEqual(ingest_crop_calendar_csv(path), 1)
        rule = database.get_crop_calendar_rule("district:test:state", "maize")
        self.assertEqual(rule["source"], "State Agriculture Dept")
        self.assertEqual(rule["sowing_start"], "06-01")
        stage = estimate_growth_stage("Maize", "2026-01-01", "2026-01-12", rule["lifecycle_stages"])
        self.assertEqual(stage["growth_stage"], "Emergence")
        self.assertEqual(stage["lifecycle_source"], "Imported crop calendar")
        self.assertIsNone(database.get_crop_calendar_rule("another:district", "Maize"))

    def test_boundary_geojson_point_match_respects_holes_and_returns_only_source_properties(self):
        feature = {"type": "Feature", "properties": {"district_name": "Example", "panchayat_code": "P-1"},
                   "geometry": {"type": "Polygon", "coordinates": [
                       [[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]],
                       [[4, 4], [6, 4], [6, 6], [4, 6], [4, 4]],
                   ]}}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "boundaries.geojson"
            path.write_text(json.dumps({"type": "FeatureCollection", "features": [feature]}), encoding="utf-8")
            matched = resolve_boundary(2, 2, path)
            hole = resolve_boundary(5, 5, path)
        self.assertEqual(matched["district"], "Example")
        self.assertEqual(matched["boundary_id"], "P-1")
        self.assertEqual(matched["boundary_level"], "district")
        self.assertIsNone(hole)

    def test_chronological_model_training_persists_metrics_and_forecasts_only_validated_models(self):
        start = date(2022, 1, 1)
        rows = []
        for index in range(620):
            rainfall = 0.0 if index % 24 < 8 else 4.0
            if index % 71 == 35:
                rainfall = 70.0
            rows.append({"location_id": "district:fixture", "date": (start + timedelta(days=index)).isoformat(),
                         "rainfall_mm": rainfall, "normal_rainfall_mm": 1.2,
                         "temperature_c": 25 + index % 9, "humidity_percent": 60 + index % 20,
                         "wind_kmh": 7 + index % 4, "pressure_hpa": 1000 + index % 5,
                         "enso_index": (index // 30) % 5 - 2, "iod_index": (index // 20) % 3 - 1,
                         "mjo_rmm1": index % 7 - 3, "mjo_rmm2": index % 5 - 2,
                         "mjo_phase": index % 8 + 1, "mjo_amplitude": 1.2,
                         "onset_event": int(index % 80 == 10), "false_onset_event": int(index % 90 == 45),
                         "source": "fixed-test-fixture"})
        run = train_location_model(rows, "district:fixture", min_test_samples=10, epochs=80, regression_epochs=100)
        forecast = forecast_with_model_run(rows[-90:], run)
        self.assertTrue(run["validated"])
        self.assertTrue(run["metrics"]["dry_spell_event:14"]["test_n"] >= 10)
        self.assertIn("dry_spell_event:14", run["models"])
        self.assertTrue(forecast["14"]["validated"])
        self.assertEqual(run["metrics"]["dry_spell_event:14"]["status"], "Chronological held-out metrics computed.")

    def test_ensemble_member_probability_helpers(self):
        daily = {"precipitation_sum_member01": [0, 1], "precipitation_sum_member02": [None, 2],
                 "precipitation_sum_member03": [3, 4]}
        self.assertEqual(len(_ensemble_members(daily)), 2)
        self.assertEqual(_max_dry_run([0, 0, 3, 0, 0, 0]), 3)

    def test_sowing_decision_waits_when_dry_risk_is_high_without_irrigation(self):
        forecast = {"available": True, "horizons": [{"days": 14, "available": True,
                    "dry_spell_probability": .7, "heavy_rain_probability": .1}]}
        result = sowing_decision(forecast, "Maize", False, 14, "Seedling", "Can wait")
        self.assertEqual(result["decision"], "WAIT")
        self.assertTrue(result["not_a_guarantee"])

    def test_explanation_surfaces_false_onset_only_from_a_validated_local_model(self):
        forecast = {"horizons": [], "recent_rainfall": {}, "climate_drivers": {"drivers": []},
                    "source": {}, "events": {}, "agri_model": {"horizons": {
                        "14": {"validated": True, "predictions": {"false_onset_event": .63}}}}}
        self.assertEqual(explain_forecast(forecast, 14)["false_onset"]["value"], .63)
        forecast["agri_model"]["horizons"]["14"]["validated"] = False
        self.assertIsNone(explain_forecast(forecast, 14)["false_onset"]["value"])


class ExistingApplicationApiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.original_db_path = database.DB_PATH
        self.original_upload_dir = app_module.UPLOAD_DIR
        database.DB_PATH = Path(self.tmp.name) / "test.db"
        app_module.UPLOAD_DIR = Path(self.tmp.name) / "uploads"
        app_module.UPLOAD_DIR.mkdir()
        database.init_db()
        app_module.app.config["TESTING"] = True
        self.client = app_module.app.test_client()

    def tearDown(self):
        database.DB_PATH = self.original_db_path
        app_module.UPLOAD_DIR = self.original_upload_dir
        self.tmp.cleanup()

    def test_database_dashboard_location_and_language_endpoints(self):
        self.assertEqual(self.client.get("/api/health").status_code, 200)
        self.assertEqual(self.client.get("/api/dashboard").status_code, 200)
        self.assertIsNone(self.client.get("/api/location").json["location"])
        saved = self.client.post("/api/location", json={"label": "Test District", "latitude": 17.4,
                                    "longitude": 78.4, "district": "Test District", "state": "Test State",
                                    "location_id": "district:test:test-state", "village_cluster": "Example cluster"})
        self.assertEqual(saved.status_code, 200)
        self.assertEqual(self.client.get("/api/location").json["location"]["district"], "Test District")
        self.assertEqual(self.client.get("/api/location").json["location"]["location_id"], "district:test:test-state")
        self.assertEqual(self.client.get("/api/location").json["location"]["village_cluster"], "Example cluster")
        self.assertEqual(self.client.get("/api/languages").status_code, 200)
        self.assertEqual(len(self.client.get("/api/languages").json["languages"]), 6)
        self.assertEqual(self.client.get("/api/location/reverse?latitude=invalid&longitude=0").status_code, 400)
        self.assertEqual(self.client.get("/api/monsoon/model-performance").json["runs"], [])
        self.assertEqual(self.client.get("/api/dashboard").json["summary"]["active_crops"], 0)

    @patch.object(app_module, "generate_forecast")
    def test_invalid_explicit_forecast_coordinates_do_not_fall_back_to_saved_location(self, generate):
        self.client.post("/api/location", json={"label": "Saved District", "latitude": 17.4,
                           "longitude": 78.4, "location_id": "district:saved:state"})
        generate.return_value = {"available": False, "horizons": [], "events": {}, "source": {},
                                 "recent_rainfall": {}, "climate_drivers": {"drivers": []},
                                 "advisory": []}
        response = self.client.get("/api/monsoon/forecast?latitude=91&longitude=0")
        self.assertEqual(response.status_code, 200)
        generate.assert_called_once_with(None, None, None, None)

    @patch.object(app_module, "search_locations", return_value=[{"name": "Test City", "latitude": 1, "longitude": 2}])
    def test_manual_location_search(self, search):
        result = self.client.get("/api/location/search?q=Test City")
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json["results"][0]["name"], "Test City")
        search.assert_called_once_with("Test City")

    def test_configured_authoritative_boundary_enriches_point_without_claiming_area_risk(self):
        feature = {"type": "Feature", "properties": {"district_name": "Test District",
                   "panchayat_name": "Test Cluster", "panchayat_code": "P-9"},
                   "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]]}}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "official.geojson"
            path.write_text(json.dumps({"type": "FeatureCollection", "features": [feature]}), encoding="utf-8")
            def forecast(latitude, longitude, crop, location):
                return {"available": True, "location": location, "daily": [], "horizons": [], "events": {},
                        "source": {}, "recent_rainfall": {}, "climate_drivers": {"drivers": []}, "advisory": []}
            with patch.dict("os.environ", {"AGRISHIELD_BOUNDARY_GEOJSON": str(path)}), \
                 patch.object(app_module, "generate_forecast", side_effect=forecast):
                result = self.client.get("/api/monsoon/risk-map?latitude=2&longitude=2").json
        self.assertTrue(result["boundary_match"])
        self.assertEqual(result["location"]["village_cluster"], "Test Cluster")
        self.assertEqual(result["spatial_resolution"], "selected weather grid point; no area aggregation")

    def test_crop_creation_and_timeline(self):
        created = self.client.post("/api/crops", json={"crop_name": "Maize", "field_name": "QA field",
                                    "planting_date": date.today().isoformat(), "location": "Test",
                                    "latitude": 17.4, "longitude": 78.4, "field_area": 2.5,
                                    "irrigation_type": "drip"})
        self.assertEqual(created.status_code, 201)
        crop_id = created.json["crop"]["id"]
        self.assertEqual(created.json["crop"]["field_area"], 2.5)
        self.assertEqual(created.json["crop"]["irrigation_type"], "drip")
        self.assertEqual(self.client.get(f"/api/crops/{crop_id}").status_code, 200)
        self.assertEqual(self.client.get(f"/api/crop-timeline?crop_id={crop_id}").status_code, 200)
        updated = self.client.put(f"/api/crops/{crop_id}", json={"crop_name": "Maize", "field_name": "Edited field",
                                    "planting_date": date.today().isoformat(), "latitude": 17.4, "longitude": 78.4,
                                    "field_area": 3, "irrigation_type": "canal"})
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json["crop"]["field_name"], "Edited field")
        archived = self.client.delete(f"/api/crops/{crop_id}")
        self.assertEqual(archived.json["status"], "archived")
        self.assertEqual(self.client.get(f"/api/crops/{crop_id}").status_code, 404)

    def test_future_sowing_creates_planned_pre_sowing_state(self):
        future = (date.today() + timedelta(days=14)).isoformat()
        result = self.client.post("/api/crops", json={"crop_name": "Tomato", "field_name": "Future field",
                                    "planting_date": future, "latitude": 17.4, "longitude": 78.4,
                                    "field_area": 1, "irrigation_type": "rainfed"})
        self.assertEqual(result.status_code, 201)
        self.assertEqual(result.json["crop"]["status"], "planned")
        self.assertIsNone(result.json["crop"]["days_since_planting"])
        self.assertEqual(result.json["crop"]["growth_stage"], "Not planted yet")

    def test_planned_crop_becomes_active_when_real_sowing_date_arrives(self):
        future = (date.today() + timedelta(days=2)).isoformat()
        result = self.client.post("/api/crops", json={"crop_name": "Tomato", "field_name": "Planned field",
                                    "planting_date": future, "latitude": 17.4, "longitude": 78.4,
                                    "field_area": 1, "irrigation_type": "rainfed"})
        crop_id = result.json["crop"]["id"]
        with database.get_connection() as connection:
            connection.execute("UPDATE crops SET planting_date=?,status='planned' WHERE id=?",
                               ((date.today() - timedelta(days=1)).isoformat(), crop_id))
        activated = database.get_crop(crop_id)
        self.assertEqual(activated["status"], "active")
        self.assertEqual(self.client.get(f"/api/crops/{crop_id}").json["crop"]["days_since_planting"], 1)

    def test_imported_crop_calendar_is_attached_to_matching_crop_profile(self):
        result = self.client.post("/api/crops", json={"crop_name": "Maize", "field_name": "Calendar field",
                                    "planting_date": date.today().isoformat(), "latitude": 17.4,
                                    "longitude": 78.4, "location_id": "district:test:state",
                                    "field_area": 1, "irrigation_type": "rainfed"})
        crop_id = result.json["crop"]["id"]
        database.upsert_crop_calendar_rules([{"location_id": "district:test:state", "crop_name": "Maize",
            "source": "State Agriculture Dept", "sowing_start": "06-01", "sowing_end": "07-15",
            "water_requirement_mm_day": 4.2, "lifecycle_stages": [{"day": 0, "stage": "Emergence"}],
            "version": "v1"}])
        crop = self.client.get(f"/api/crops/{crop_id}").json["crop"]
        self.assertEqual(crop["growth_stage"], "Emergence")
        self.assertEqual(crop["crop_calendar"]["source"], "State Agriculture Dept")

    @patch.object(app_module, "generate_forecast")
    def test_sowing_window_refuses_unverified_suitability(self, generate):
        generate.return_value = {"available": True, "horizons": [{"days": 14, "expected_rainfall_mm": 20,
                              "dry_spell_probability": .4}], "events": {"onset_probability": None},
                              "recent_rainfall": {"available": True, "daily": []},
                              "source": {"name": "test", "generated_at": "2026-01-01T00:00:00Z"},
                              "climate_drivers": {"drivers": []}, "model": {}, "location": {"latitude": 17.4, "longitude": 78.4}}
        response = self.client.get("/api/monsoon/sowing-window?latitude=17.4&longitude=78.4&crop_name=Maize")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["assessment"]["suitability"], "unavailable")

    @patch.object(app_module, "generate_forecast")
    def test_alerts_are_persisted_acknowledgeable_and_based_on_provider_provenance(self, generate):
        generate.return_value = {"available": True, "horizons": [{"days": 14, "dry_spell_probability": .6,
                              "heavy_rain_probability": .3, "probability_basis": "raw provider members"}],
                              "events": {}, "daily": [], "advisory": [], "climate_drivers": {"drivers": []},
                              "source": {"name": "Fixture provider", "generated_at": "2026-09-30T00:00:00Z"},
                              "recent_rainfall": {"available": True, "daily": [], "last_observation_date": "2026-09-20"},
                              "location": {"latitude": 17, "longitude": 78}}
        response = self.client.get("/api/monsoon/alerts?latitude=17&longitude=78")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json["alerts"]), 2)
        self.assertTrue(all(item["source"] == "Fixture provider" for item in response.json["alerts"]))
        alert_id = response.json["alerts"][0]["id"]
        self.assertEqual(self.client.post(f"/api/monsoon/alerts/{alert_id}/acknowledge").json["status"], "acknowledged")

    def test_climate_ingestion_and_model_run_storage_use_sqlite(self):
        with tempfile.TemporaryDirectory() as directory:
            csv_path = Path(directory) / "climate.csv"
            csv_path.write_text("date,rainfall_mm,temperature_c\n2025-01-01,2,25\n2025-01-02,0,24\n", encoding="utf-8")
            self.assertEqual(ingest_csv(csv_path, "district:test", "measured-station"), 2)
        stored = database.get_climate_observations("district:test")
        self.assertEqual(len(stored), 2)
        self.assertEqual(stored[0]["rainfall_mm"], 2.0)
        run = {"model_version": "test-version", "location_id": "district:test", "algorithm": "fixture",
               "status": "partially_validated", "validated": True, "sample_count": 2,
               "models": {"dry:7": {"weights": [1]}}, "metrics": {"dry:7": {"brier_score": .2}}}
        database.save_model_run(run)
        public = self.client.get("/api/monsoon/model-performance?location_id=district:test").json
        self.assertTrue(public["available"])
        self.assertEqual(public["runs"][0]["metrics"]["dry:7"]["brier_score"], .2)
        self.assertIsNone(public["runs"][0]["models"])

    @patch.object(app_module, "generate_forecast")
    def test_outlook_risk_map_advisory_and_sowing_endpoints(self, generate):
        generated = {"available": True, "horizons": [{"days": 7, "available": True,
                     "expected_rainfall_mm": 20, "rainfall_probability": .6,
                     "dry_spell_probability": .7, "heavy_rain_probability": .1,
                     "onset_probability": None, "rainfall_anomaly_mm": None}],
                     "daily": [], "events": {"onset_status": "Data unavailable"},
                     "advisory": ["Check soil moisture."], "data_status": "Test forecast",
                     "location": {"latitude": 17, "longitude": 78}}
        generate.return_value = generated
        self.assertEqual(self.client.get("/api/monsoon/outlook?latitude=17&longitude=78").status_code, 200)
        self.assertFalse(self.client.get("/api/monsoon/risk-map?latitude=17&longitude=78").json["boundaries_available"])
        self.assertEqual(self.client.get("/api/monsoon/advisory?latitude=17&longitude=78").json["advisory"], ["Check soil moisture."])
        decision = self.client.post("/api/monsoon/sowing-decision", json={"latitude": 17, "longitude": 78,
                                    "horizon_days": 7, "crop_name": "Maize", "irrigation_available": False})
        self.assertEqual(decision.status_code, 200)
        self.assertEqual(decision.json["decision"]["decision"], "WAIT")
        self.assertEqual(self.client.post("/api/monsoon/sowing-decision", json={"horizon_days": 9}).status_code, 400)

    @patch.object(app_module, "analyze_image")
    def test_existing_crop_and_quick_image_uploads_still_work(self, analyze):
        analyze.side_effect = lambda path, crop_name, description, latitude=None, longitude=None: app_module.pending_diagnosis(crop_name, description)
        crop = self.client.post("/api/crops", json={"crop_name": "Maize", "field_name": "Upload QA",
                                  "planting_date": date.today().isoformat(), "latitude": 17.4, "longitude": 78.4,
                                  "field_area": 1, "irrigation_type": "rainfed"}).json["crop"]
        upload = {"image": (BytesIO(test_png()), "leaf.png"), "scan_date": "2026-09-30", "description": "test scan"}
        scan = self.client.post(f"/api/crops/{crop['id']}/scans", data=upload, content_type="multipart/form-data")
        self.assertEqual(scan.status_code, 201, scan.json)
        self.assertEqual(self.client.get(f"/api/crops/{crop['id']}").json["crop"]["scan_count"], 1)
        quick = self.client.post("/api/disease/analyze", data={"crop_name": "Maize", "image": (BytesIO(test_png()), "quick.png")}, content_type="multipart/form-data")
        self.assertEqual(quick.status_code, 201)
        self.assertEqual(quick.json["quick_diagnosis"]["diagnosis_status"], "pending_model")


if __name__ == "__main__":
    unittest.main()
