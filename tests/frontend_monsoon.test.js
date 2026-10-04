import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { mt, translateCropStage, formatMt } from "../src/monsoonI18n.js";

const languages = ["en", "hi", "te", "ta", "kn", "mr"];
const appSource = readFileSync(new URL("../src/App.jsx", import.meta.url), "utf8");

test("Monsoon navigation and farmer actions have translations in every supported language", () => {
  for (const key of ["monsoon", "sowingWindow", "alerts", "modelPerformance", "useGps", "search",
    "addCrop", "createCrop", "confirmCrop", "reviewSowing", "assessWindow", "acknowledge", "refresh",
    "selectedRiskMap", "weatherMonitoring", "expectedRainWindow", "dataTransparency", "forecastRetrieved",
    "riskModelBasis", "riskProviderBasis", "riskLayer"]) {
    const english = mt(key, "en");
    assert.ok(english && english !== key, `${key} must have an English label`);
    for (const language of languages.slice(1)) {
      const translated = mt(key, language);
      assert.ok(translated && translated !== english, `${key} must be translated for ${language}`);
    }
  }
});

test("stage and advisory templates translate and substitute crop context", () => {
  for (const language of languages.slice(1)) {
    assert.notEqual(translateCropStage("Seedling", language), "Seedling");
    assert.notEqual(translateCropStage("Tuber bulking", language), "Tuber bulking");
    const label = formatMt("irrigationAdvice", language, { crop: "Maize", stage: translateCropStage("Seedling", language) });
    assert.ok(label.includes("Maize"));
  }
});

test("primary navigation, location, crop, forecast and risk controls are wired to handlers", () => {
  for (const id of ["monsoon", "dashboard", "quick", "crop", "timeline", "sowingWindow", "alerts", "modelPerformance"])
    assert.ok(appSource.includes(`id: "${id}"`) || appSource.includes(`page === "${id}"`), `Missing ${id} page`);
  for (const handler of ["location.locate", "location.select(result)", "archiveCrop(crop.id)", "updateCrop(editingId",
    "createCrop(cropPayload)", "createTimelineScan(crop.id", "setMapLayer(event.target.value)",
    "setHorizon(Number(event.target.value))", "makeDecision", "acknowledge(alert.id)",
    "setLanguage(event.target.value)", "onSubmit={submit}"])
    assert.ok(appSource.includes(handler), `Missing frontend action ${handler}`);
});

test("crop-empty and data-unavailable states are explicit", () => {
  assert.ok(appSource.includes("t(\"noActiveCrop\")"));
  assert.ok(appSource.includes("t(\"forecastUnavailable\")"));
  assert.ok(appSource.includes("onClick={location.locate}"));
});
