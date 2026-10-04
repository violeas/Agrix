import React, { useEffect, useMemo, useRef, useState } from "react";
import {
  AlertCircle,
  Activity,
  AlertTriangle,
  BarChart3,
  CalendarDays,
  Camera,
  CloudRain,
  CheckCircle2,
  ChevronRight,
  ClipboardList,
  Clock3,
  FileText,
  History,
  Home,
  ImagePlus,
  Languages,
  Leaf,
  LineChart as LineChartIcon,
  Loader2,
  MapPin,
  Microscope,
  Plus,
  RefreshCw,
  Search,
  ShieldCheck,
  Sprout,
  Upload,
} from "lucide-react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  compareScan,
  createCrop,
  createTimelineScan,
  getCrop,
  getDashboard,
  getWeather,
  imageUrl,
  runQuickDiagnosis,
  getMonsoonForecast,
  getClimateDrivers,
  getSavedLocation,
  getSowingDecision,
  getSowingWindow,
  getMonsoonAlerts,
  getModelPerformance,
  acknowledgeAlert,
  updateCrop,
  archiveCrop,
  reverseGeocode,
  saveLocation,
  searchLocations,
} from "./services/aiApi";
import { formatMt, mt, translateCropStage } from "./monsoonI18n";

const navItems = [
  { id: "monsoon", icon: CloudRain },
  { id: "dashboard", icon: Home },
  { id: "quick", icon: Microscope },
  { id: "crop", icon: Sprout },
  { id: "timeline", icon: History },
  { id: "sowingWindow", icon: Sprout },
  { id: "alerts", icon: AlertTriangle },
  { id: "modelPerformance", icon: LineChartIcon },
];

const languageOptions = [
  { code: "en", label: "English" },
  { code: "hi", label: "Hindi" },
  { code: "te", label: "Telugu" },
  { code: "ta", label: "Tamil" },
  { code: "kn", label: "Kannada" },
  { code: "mr", label: "मराठी" },
];

const labelTranslations = {
  hi: {
    "Recommended Actions": "अनुशंसित कार्य",
    Precautions: "सावधानियां",
    "Medicine Guidance": "दवा मार्गदर्शन",
    "Fertilizer Guidance": "खाद मार्गदर्शन",
    "Natural Remedies": "प्राकृतिक उपाय",
    "Next Check": "अगली जांच",
    "Do Not": "क्या न करें",
    "Visual Evidence": "दृश्य प्रमाण",
    "Farmer Observation": "किसान अवलोकन",
    Diagnosis: "निदान",
    Reliability: "विश्वसनीयता",
    Severity: "गंभीरता",
    "Model Confidence": "मॉडल विश्वास",
    "Top Model Matches": "शीर्ष मॉडल मिलान",
  },
  te: {
    "Recommended Actions": "సూచించిన చర్యలు",
    Precautions: "జాగ్రత్తలు",
    "Medicine Guidance": "మందు సూచన",
    "Fertilizer Guidance": "ఎరువు సూచన",
    "Natural Remedies": "సహజ పరిష్కారాలు",
    "Next Check": "తదుపరి తనిఖీ",
    "Do Not": "చేయకూడనివి",
    "Visual Evidence": "దృశ్య ఆధారం",
    "Farmer Observation": "రైతు గమనిక",
    Diagnosis: "నిర్ధారణ",
    Reliability: "నమ్మకత",
    Severity: "తీవ్రత",
    "Model Confidence": "మోడల్ నమ్మకం",
    "Top Model Matches": "మోడల్ ప్రధాన ఫలితాలు",
  },
  ta: {
    "Recommended Actions": "பரிந்துரைக்கப்பட்ட நடவடிக்கைகள்",
    Precautions: "முன்னெச்சரிக்கைகள்",
    "Medicine Guidance": "மருந்து வழிகாட்டல்",
    "Fertilizer Guidance": "உர வழிகாட்டல்",
    "Natural Remedies": "இயற்கை முறைகள்",
    "Next Check": "அடுத்த ஆய்வு",
    "Do Not": "செய்ய வேண்டாம்",
    "Visual Evidence": "காட்சி ஆதாரம்",
    "Farmer Observation": "விவசாயி குறிப்பு",
    Diagnosis: "நோயறிதல்",
    Reliability: "நம்பகத்தன்மை",
    Severity: "தீவிரம்",
    "Model Confidence": "மாடல் நம்பிக்கை",
    "Top Model Matches": "முக்கிய மாடல் பொருத்தங்கள்",
  },
  kn: {
    "Recommended Actions": "ಶಿಫಾರಸು ಕ್ರಮಗಳು",
    Precautions: "ಮುನ್ನೆಚ್ಚರಿಕೆಗಳು",
    "Medicine Guidance": "ಔಷಧ ಮಾರ್ಗದರ್ಶನ",
    "Fertilizer Guidance": "ರಸಗೊಬ್ಬರ ಮಾರ್ಗದರ್ಶನ",
    "Natural Remedies": "ನೈಸರ್ಗಿಕ ಪರಿಹಾರಗಳು",
    "Next Check": "ಮುಂದಿನ ಪರಿಶೀಲನೆ",
    "Do Not": "ಮಾಡಬೇಡಿ",
    "Visual Evidence": "ದೃಶ್ಯ ಸಾಕ್ಷ್ಯ",
    "Farmer Observation": "ರೈತರ ಗಮನಿಕೆ",
    Diagnosis: "ನಿರ್ಣಯ",
    Reliability: "ವಿಶ್ವಾಸಾರ್ಹತೆ",
    Severity: "ತೀವ್ರತೆ",
    "Model Confidence": "ಮಾದರಿ ವಿಶ್ವಾಸ",
    "Top Model Matches": "ಮುಖ್ಯ ಮಾದರಿ ಹೊಂದಾಣಿಕೆಗಳು",
  },
};

function tr(label, language) {
  return labelTranslations[language]?.[label] || label;
}

function userObservations(record) {
  const hiddenPhrases = [
    "model",
    "classifier",
    "classes",
    "unrelated crop",
    "farmer selected crop",
    "image has enough",
    "quality",
  ];
  const cleanEvidence = (record.evidence || []).filter((item) => {
    const text = String(item).toLowerCase();
    return !hiddenPhrases.some((phrase) => text.includes(phrase));
  });
  return [...new Set([...(record.visual_indicators || []), ...cleanEvidence])];
}

function localDateISO(date = new Date()) {
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
  return local.toISOString().slice(0, 10);
}

function freshCropForm() {
  return {
    crop_name: "",
    field_name: "",
    planting_date: "",
    location: "",
    field_area: "",
    field_area_unit: "acre",
    irrigation_type: "",
    notes: "",
  };
}

function formatDate(value) {
  if (!value) return "Not recorded";
  return new Intl.DateTimeFormat("en", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(new Date(`${value}`.slice(0, 10)));
}

function formatDateTime(value) {
  if (!value) return "Not recorded";
  return new Intl.DateTimeFormat("en", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function todayISO() {
  return localDateISO();
}

function App() {
  const [page, setPage] = useState("monsoon");
  const [dashboard, setDashboard] = useState(null);
  const [crops, setCrops] = useState([]);
  const [selectedCropId, setSelectedCropId] = useState("");
  const [selectedCrop, setSelectedCrop] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [refreshKey, setRefreshKey] = useState(0);
  const [language, setLanguage] = useState(() => localStorage.getItem("agrishield-language") || "en");
  const location = useLocationManager();
  const t = (key) => mt(key, language);

  const refreshData = async (preferredCropId = selectedCropId) => {
    setError("");
    const payload = await getDashboard();
    setDashboard(payload);
    setCrops(payload.crops || []);

    const nextId =
      preferredCropId && payload.crops?.some((crop) => String(crop.id) === String(preferredCropId))
        ? String(preferredCropId)
        : payload.crops?.[0]?.id
          ? String(payload.crops[0].id)
          : "";
    setSelectedCropId(nextId);
    return nextId;
  };

  useEffect(() => {
    let active = true;
    setLoading(true);
    refreshData()
      .catch((err) => {
        if (active) setError(err.message);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [refreshKey]);

  useEffect(() => {
    let active = true;
    if (!selectedCropId) {
      setSelectedCrop(null);
      return undefined;
    }
    getCrop(selectedCropId)
      .then((payload) => {
        if (active) setSelectedCrop(payload.crop);
      })
      .catch((err) => {
        if (active) setError(err.message);
      });
    return () => {
      active = false;
    };
  }, [selectedCropId, refreshKey]);

  const reload = () => setRefreshKey((value) => value + 1);

  const handleCropCreated = async (crop) => {
    const nextId = await refreshData(String(crop.id));
    setSelectedCropId(nextId);
    setPage("timeline");
  };

  const handleScanCreated = async (crop) => {
    setSelectedCrop(crop);
    await refreshData(String(crop.id));
  };

  const handleCropArchived = async (cropId) => {
    const keepId = String(cropId) === String(selectedCropId) ? "" : selectedCropId;
    await refreshData(keepId);
  };

  const content = useMemo(() => {
    if (loading) {
      return <LoadingState />;
    }
    if (page === "quick") {
      return <QuickDiagnosis language={language} location={location} onRefresh={reload} />;
    }
    if (page === "crop") {
      return (
        <MyCrop
          crops={crops}
          location={location}
          language={language}
          onCreated={handleCropCreated}
          onRefresh={refreshData}
          onArchived={handleCropArchived}
          onOpenLocation={() => setPage("monsoon")}
          onOpenTimeline={(cropId) => {
            setSelectedCropId(String(cropId));
            setPage("timeline");
          }}
        />
      );
    }
    if (page === "timeline") {
      return (
        <CropTimeline
          crops={crops}
          selectedCropId={selectedCropId}
          selectedCrop={selectedCrop}
          setSelectedCropId={setSelectedCropId}
          onScanCreated={handleScanCreated}
          openCropPage={() => setPage("crop")}
          language={language}
          location={location}
        />
      );
    }
    if (page === "monsoon") {
      return <MonsoonIntelligence crops={crops} selectedCropId={selectedCropId} location={location} language={language} onAddCrop={() => setPage("crop")} />;
    }
    if (page === "sowingWindow") return <SowingWindowPage crops={crops} selectedCropId={selectedCropId} location={location} language={language} onOpenLocation={() => setPage("monsoon")} />;
    if (page === "alerts") return <AlertsPage location={location} language={language} />;
    if (page === "modelPerformance") return <ModelPerformancePage location={location} language={language} />;
    return (
      <Dashboard
        dashboard={dashboard}
        crops={crops}
        onCreateCrop={() => setPage("crop")}
        onQuickDiagnosis={() => setPage("quick")}
        onOpenCrop={(cropId) => {
          setSelectedCropId(String(cropId));
          setPage("timeline");
        }}
        weather={location.weather}
        location={location}
        language={language}
        onOpenMonsoon={() => setPage("monsoon")}
      />
    );
  }, [loading, page, dashboard, crops, selectedCropId, selectedCrop, language, location]);

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <button className="brand" type="button" onClick={() => setPage("dashboard")}>
          <span className="brand-mark">
            <Leaf size={24} />
          </span>
          <span>
            <strong>AgriShield</strong>
            <small>Monsoon & crop intelligence</small>
          </span>
        </button>

        <nav className="side-nav" aria-label="AgriShield navigation">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <button
                className={page === item.id ? "active" : ""}
                key={item.id}
                type="button"
                onClick={() => setPage(item.id)}
              >
                <Icon size={18} />
                <span>{mt(item.id, language)}</span>
              </button>
            );
          })}
        </nav>
      </aside>

      <main className="main-panel">
        <header className="topbar">
          <div>
            <p className="eyebrow">Crop lifecycle command center</p>
            <h1>{mt(page, language)}</h1>
          </div>
          <div className="topbar-actions">
            <button className="icon-button" type="button" onClick={reload} aria-label={t("refresh")} title={t("refresh")}>
              <RefreshCw size={18} />
            </button>
            <button className="environment-chip location-header-button" type="button" onClick={() => setPage("monsoon")} aria-label="Open location and monsoon outlook">
              <MapPin size={16} />
              <span>{location.label || t("chooseLocation")}</span>
            </button>
            {location.weather?.available && (
              <div className="weather-chip">
                <Activity size={16} />
                <span>
                  {location.weather.temperature_c} C | {location.weather.humidity_percent}% humidity | {location.weather.risk_level}
                </span>
              </div>
            )}
            <label className="translate-chip">
              <Languages size={16} />
              <select value={language} onChange={(event) => { localStorage.setItem("agrishield-language", event.target.value); setLanguage(event.target.value); }} aria-label="Select language">
                {languageOptions.map((option) => (
                  <option value={option.code} key={option.code}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
          </div>
        </header>

        {error && (
          <div className="alert-banner">
            <AlertTriangle size={18} />
            <span>{error}</span>
          </div>
        )}

        {content}
      </main>
    </div>
  );
}

function MonsoonIntelligence({ crops, selectedCropId, location, language, onAddCrop }) {
  const [forecast, setForecast] = useState(null);
  const [currentWeather, setCurrentWeather] = useState(location.weather || null);
  const [horizon, setHorizon] = useState(7);
  const [loadingForecast, setLoadingForecast] = useState(true);
  const [forecastError, setForecastError] = useState("");
  const [cropId, setCropId] = useState(selectedCropId || "");
  const [query, setQuery] = useState("");
  const [searchResults, setSearchResults] = useState([]);
  const [searchError, setSearchError] = useState("");
  const [searching, setSearching] = useState(false);
  const [irrigation, setIrrigation] = useState(false);
  const [decisionCropName, setDecisionCropName] = useState("");
  const [decisionStage, setDecisionStage] = useState("");
  const [sowingPreference, setSowingPreference] = useState("Sow as soon as conditions allow");
  const [decisionHorizon, setDecisionHorizon] = useState(14);
  const [decision, setDecision] = useState(null);
  const [decisionError, setDecisionError] = useState("");
  const [decisionLoading, setDecisionLoading] = useState(false);
  const [advancedView, setAdvancedView] = useState(false);
  const [mapLayer, setMapLayer] = useState("dry_spell");
  const t = (key) => mt(key, language);
  const activeCrop = crops.find((crop) => String(crop.id) === String(cropId));
  const forecastLocation = activeCrop?.latitude != null && activeCrop?.longitude != null
    ? { ...location, ...activeCrop, label: activeCrop.location || location.label }
    : location;

  useEffect(() => {
    let active = true;
    const sameAsSaved = Number(forecastLocation.latitude) === Number(location.latitude) &&
      Number(forecastLocation.longitude) === Number(location.longitude);
    if (sameAsSaved) {
      setCurrentWeather(location.weather || null);
      return () => { active = false; };
    }
    if (forecastLocation.latitude == null || forecastLocation.longitude == null) {
      setCurrentWeather(null);
      return () => { active = false; };
    }
    setCurrentWeather(null);
    getWeather(forecastLocation.latitude, forecastLocation.longitude)
      .then((payload) => { if (active) setCurrentWeather(payload.weather); })
      .catch(() => { if (active) setCurrentWeather(null); });
    return () => { active = false; };
  }, [forecastLocation.latitude, forecastLocation.longitude, location.latitude, location.longitude, location.weather]);

  useEffect(() => { setCropId(selectedCropId || ""); }, [selectedCropId]);
  useEffect(() => {
    if (activeCrop) {
      setDecisionCropName(activeCrop.crop_name);
      setDecisionStage(activeCrop.growth_stage || "");
    } else {
      setDecisionCropName("");
      setDecisionStage("");
    }
  }, [activeCrop?.id, activeCrop?.growth_stage]);
  useEffect(() => {
    let active = true;
    setLoadingForecast(true);
    setForecastError("");
    setForecast(null);
    getMonsoonForecast(forecastLocation, cropId, { horizonDays: horizon }).then((payload) => {
      if (active) setForecast(payload.forecast);
    }).catch((err) => {
      if (active) { setForecast(null); setForecastError(err.message); }
    }).finally(() => { if (active) setLoadingForecast(false); });
    return () => { active = false; };
  }, [cropId, activeCrop?.latitude, activeCrop?.longitude, activeCrop?.location_id,
      location.latitude, location.longitude, location.location_id, horizon]);

  const outlook = forecast?.horizons?.find((item) => item.days === Number(horizon));
  const mlOutlook = forecast?.agri_model?.horizons?.[String(horizon)];
  const localPredictions = mlOutlook?.validated ? (mlOutlook.predictions || {}) : {};
  const dryRiskValue = localPredictions.dry_spell_event ?? outlook?.dry_spell_probability;
  const heavyRiskValue = localPredictions.heavy_rain_event ?? outlook?.heavy_rain_probability;
  const onsetRiskValue = localPredictions.onset_event ?? null;
  const falseOnsetRiskValue = localPredictions.false_onset_event ?? null;
  const anomalyValue = localPredictions.rainfall_anomaly_mm ?? null;
  const selectedRiskValue = mapLayer === "dry_spell" ? dryRiskValue
    : mapLayer === "heavy_rain" ? heavyRiskValue
      : mapLayer === "onset" ? onsetRiskValue : null;
  const selectedRiskUsesModel = mapLayer === "dry_spell" ? localPredictions.dry_spell_event != null
    : mapLayer === "heavy_rain" ? localPredictions.heavy_rain_event != null
      : mapLayer === "onset" ? onsetRiskValue != null : anomalyValue != null;
  const percent = (value) => value == null ? t("dataUnavailable") : `${Math.round(value * 100)}%`;
  const amount = (value) => value == null ? t("dataUnavailable") : `${value} mm`;
  const submitSearch = async (event) => {
    event.preventDefault();
    if (query.trim().length < 2) { setSearchError("Enter at least two characters."); return; }
    setSearching(true); setSearchError(""); setSearchResults([]);
    try { const payload = await searchLocations(query.trim()); setSearchResults(payload.results || []); if (!payload.results?.length) setSearchError("No matching locations found."); }
    catch (err) { setSearchError(err.message); }
    finally { setSearching(false); }
  };
  const makeDecision = async () => {
    setDecision(null); setDecisionError(""); setDecisionLoading(true);
    if (!decisionCropName.trim()) {
      setDecisionLoading(false);
      setDecisionError(t("selectCrop"));
      return;
    }
    try {
      const payload = await getSowingDecision({
        latitude: forecastLocation.latitude, longitude: forecastLocation.longitude,
        crop_name: decisionCropName, crop_id: activeCrop?.crop_name === decisionCropName ? cropId : undefined,
        crop_stage: activeCrop?.growth_stage || decisionStage,
        sowing_preference: sowingPreference,
        irrigation_available: irrigation, horizon_days: Number(decisionHorizon),
      });
      setDecision(payload.decision);
    } catch (err) { setDecisionError(err.message); }
    finally { setDecisionLoading(false); }
  };
  const mapEmbed = forecastLocation.latitude != null && forecastLocation.longitude != null
    ? `https://www.openstreetmap.org/export/embed.html?bbox=${forecastLocation.longitude - .18}%2C${forecastLocation.latitude - .12}%2C${forecastLocation.longitude + .18}%2C${forecastLocation.latitude + .12}&layer=mapnik&marker=${forecastLocation.latitude}%2C${forecastLocation.longitude}`
    : "";

  return (
    <section className="content-stack">
      <SectionHeader eyebrow={t("providerOnly")} title={t("monsoon")} body={t("decisionSupport")} />
      {!location.coordinates && <article className="card welcome-card"><p className="eyebrow">AgriShield</p><h3>Welcome to AgriShield</h3><p>{t("chooseLocation")}</p><p>1. Set a location · 2. Add a crop · 3. Review provider guidance and any validated local model.</p><button className="primary-button" type="button" onClick={location.locate} disabled={location.loading}><MapPin size={17}/>{location.loading ? t("findingLocation") : t("useGps")}</button></article>}
      {!crops.some((crop) => crop.status === "active") && <article className="card empty-crop-banner"><div><p className="eyebrow">{t("cropName")}</p><h3>{t("noActiveCrop")}</h3><p>{crops.some((crop) => crop.status === "planned") ? "A planned crop is saved; its lifecycle will begin on the recorded sowing date." : "No crop record has been created. Add one when you are ready; no crop age or stage is assumed."}</p></div><button className="primary-button" type="button" onClick={onAddCrop}><Plus size={17}/>{t("addCrop")}</button></article>}
      <article className="card location-card">
        <div className="location-card-heading"><div><p className="eyebrow">{t("currentLocation")}</p><h3>{location.label || t("chooseLocation")}</h3><p className="muted">{[location.village && `Village: ${location.village}`, location.block && `Block: ${location.block}`, location.district && `District: ${location.district}`, location.state && `State: ${location.state}`, location.country].filter(Boolean).join(" · ") || "Administrative levels are shown only when the geocoder provides them."}</p></div>
          <button className="primary-button" type="button" onClick={location.locate} disabled={location.loading}><MapPin size={17}/>{location.loading ? t("findingLocation") : t("useGps")}</button></div>
        <div className="location-status-row"><span className={location.coordinates ? "status-dot available" : "status-dot"}/><span>{location.status || "Location not selected"}</span>{location.coordinates && <small>Coordinates: {Number(location.latitude).toFixed(4)}, {Number(location.longitude).toFixed(4)}</small>}</div>
        {location.error && <div className="form-error">{location.error}</div>}
        <form className="location-search" onSubmit={submitSearch}>
          <label className="field-label" htmlFor="location-search">{t("locationSearch")}<input id="location-search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="" autoComplete="off"/></label>
          <button className="secondary-button" type="submit" disabled={searching}><Search size={17}/>{searching ? t("searching") : t("search")}</button>
        </form>
        {searchError && <p className="form-error" role="status">{searchError}</p>}
        {searchResults.length > 0 && <div className="location-results" role="list" aria-label="Location search results">{searchResults.map((result, index) => <button type="button" role="listitem" key={`${result.latitude}-${result.longitude}-${index}`} onClick={() => { location.select(result); setSearchResults([]); }}><MapPin size={17}/><span><strong>{[result.name, result.district, result.state, result.country].filter(Boolean).join(", ")}</strong><small>Available level: {result.admin_level_available || "coordinates"} · coordinates saved for weather grid lookup</small></span></button>)}</div>}
      </article>

      <WeatherMonitor weather={currentWeather} language={language} />

      <div className="monsoon-controls card">
        <label>{t("cropName")}<select value={cropId} onChange={(event) => { setCropId(event.target.value); setDecision(null); }}><option value="">{t("selectCrop")}</option>{crops.map((crop) => <option key={crop.id} value={crop.id}>{crop.crop_name} · {crop.field_name}</option>)}</select></label>
        <label>{t("forecastHorizon")}<select value={horizon} onChange={(event) => setHorizon(Number(event.target.value))}>{[7, 14, 21, 30].map((days) => <option key={days} value={days}>{days} days</option>)}</select></label>
        <div className="forecast-provider-state"><strong>{loadingForecast ? "Loading weather data…" : forecast?.available ? "Weather ensemble available" : "Data unavailable"}</strong><small>{forecast?.source?.model || forecastError || (location.coordinates ? "Waiting for provider response" : "Select a location to request a forecast")}</small></div>
      </div>
      {(forecast?.data_status || forecastError) && <div className={forecast?.available ? "data-banner" : "alert-banner"} role="status"><AlertCircle size={18}/><span>{forecast?.available ? t("providerOnly") : t("forecastUnavailable")}</span></div>}

      <div className="metric-grid monsoon-metrics">
        <MetricCard title={`${horizon}-day ${t("expectedRain")}`} value={amount(outlook?.expected_rainfall_mm)} icon={CloudRain} tone="green" />
        <MetricCard title={t("providerRain")} value={percent(outlook?.rainfall_probability)} icon={Activity} tone="amber" />
        <MetricCard title={`${t("dryRisk")} · GFS member frequency`} value={percent(outlook?.dry_spell_probability)} icon={AlertTriangle} tone="red" />
        <MetricCard title={`${t("heavyRisk")} · GFS member frequency`} value={percent(outlook?.heavy_rain_probability)} icon={AlertTriangle} tone="amber" />
        <MetricCard title={t("onset")} value={t("dataUnavailable")} icon={Sprout} tone="green" />
        <MetricCard title={t("anomaly")} value={t("dataUnavailable")} icon={LineChartIcon} tone="blue" />
      </div>
      <p className="muted forecast-footnote">{outlook?.probability_basis || t("dataUnavailable")} {t("providerOnly")} {t("onsetUnavailable")}</p>
      <article className="card phase-card"><div className="card-title"><CloudRain size={20}/><div><h3>{t("monsoonPhase")}</h3><p>ACTIVE → TRANSITION → BREAK → REVIVAL</p></div></div><p>{t("phaseUnavailable")}</p></article>

      <div className="dashboard-grid">
        <article className="card map-card">
          <div className="card-title"><MapPin size={20}/><div><h3>{t("selectedRiskMap")}</h3><p>{t("gridPointOnly")}</p></div></div>
          <label className="field-label">{t("riskLayer")}<select value={mapLayer} onChange={(event) => setMapLayer(event.target.value)}>
            <option value="onset">{t("onset")}</option><option value="dry_spell">{t("dryRisk")}</option>
            <option value="heavy_rain">{t("heavyRisk")}</option><option value="anomaly">{t("anomaly")}</option>
          </select></label>
          {mapEmbed ? <iframe className="location-map" title={t("selectedRiskMap")} src={mapEmbed} loading="lazy"/> : <div className="map-unavailable"><MapPin size={22}/><p>{t("showSelectedMap")}</p></div>}
          {mapLayer === "anomaly" ? <div className="risk-bar-row"><span>{t("anomaly")}</span><div className="risk-track" aria-hidden="true"/><strong>{anomalyValue == null ? t("dataUnavailable") : `${anomalyValue > 0 ? "+" : ""}${Number(anomalyValue).toFixed(1)} mm`}</strong></div> : <RiskBar language={language} label={mapLayer === "dry_spell" ? t("dryRisk") : mapLayer === "heavy_rain" ? t("heavyRisk") : t("onset")} value={selectedRiskValue}/>}
          <p className="muted">{selectedRiskUsesModel ? t("riskModelBasis") : t("riskProviderBasis")}</p>
          <p className="muted boundary-notice">{forecast?.location?.boundary_id ? `Matched ${forecast.location.boundary_level}: ${forecast.location.village_cluster || forecast.location.block || forecast.location.district || forecast.location.state || forecast.location.boundary_id}. Risk values still refer to the selected weather grid point; no area aggregation is available.` : "Block/Panchayat boundary data unavailable for this location. No administrative risk polygons are drawn. Weather values refer to the provider grid point only."}</p>
          <div className="risk-legend"><span><i className="low"/>Lower signal</span><span><i className="moderate"/>Some ensemble members</span><span><i className="high"/>Higher member frequency</span><small>Probabilities are stated with each event; color is supplementary.</small></div>
        </article>
        <article className="card event-card">
          <div className="card-title"><CloudRain size={20}/><div><h3>Monsoon events and risk</h3><p>{t("riskModelBasis")} {t("riskProviderBasis")}</p></div></div>
          <div className="risk-list">
            <RiskBar language={language} label="Dry spell (5+ days)" value={dryRiskValue}/>
            <RiskBar language={language} label="Heavy rainfall" value={heavyRiskValue}/>
            <RiskBar language={language} label={t("onset")} value={onsetRiskValue}/>
            <RiskBar language={language} label={t("falseOnset")} value={falseOnsetRiskValue}/>
          </div>
          <div className="event-explanations"><p><strong>{t("onset")}:</strong> {onsetRiskValue == null ? t("onsetUnavailable") : `${percent(onsetRiskValue)} · ${t("riskModelBasis")}`}</p><p><strong>{t("falseOnset")}:</strong> {falseOnsetRiskValue == null ? t("falseOnsetUnavailable") : `${percent(falseOnsetRiskValue)} · ${t("riskModelBasis")}`}</p><p><strong>Break / dry spell:</strong> {forecast?.events?.break_monsoon_status || t("dataUnavailable")}</p><p><strong>Rainfall revival:</strong> {forecast?.events?.revival_status || t("dataUnavailable")}</p></div>
        </article>
      </div>

      <article className="card false-onset-card"><div className="card-title"><AlertTriangle size={20}/><div><h3>{t("falseOnset")}</h3><p>{falseOnsetRiskValue == null ? t("falseOnsetUnavailable") : `${percent(falseOnsetRiskValue)} · ${t("riskModelBasis")}`}</p></div></div><p>{t("expectedRainWindow")}: {amount(outlook?.expected_rainfall_mm)} over {horizon} days · {t("expectedDryPeriod")}: {percent(outlook?.dry_spell_probability)} raw GFS member frequency.</p><p>{t("suggestedAction")}: {t("waitOnsetContinuity")}</p></article>

      <article className="card model-output-card"><div className="card-title"><Activity size={20}/><div><h3>AgriShield trained model output</h3><p>{mlOutlook?.validated ? `${forecast.agri_model.model_version} · held-out validation available` : t("noValidatedModel")}</p></div></div>
        <div className="metric-grid">
          <MetricCard title={t("onset")} value={percent(mlOutlook?.predictions?.onset_event)} icon={Sprout} tone="green"/>
          <MetricCard title={t("falseOnset")} value={percent(mlOutlook?.predictions?.false_onset_event)} icon={AlertTriangle} tone="red"/>
          <MetricCard title={t("dryRisk")} value={percent(mlOutlook?.predictions?.dry_spell_event)} icon={Activity} tone="amber"/>
          <MetricCard title={t("heavyRisk")} value={percent(mlOutlook?.predictions?.heavy_rain_event)} icon={CloudRain} tone="red"/>
          <MetricCard title={t("anomaly")} value={mlOutlook?.predictions?.rainfall_anomaly_mm == null ? t("dataUnavailable") : `${mlOutlook.predictions.rainfall_anomaly_mm.toFixed(1)} mm`} icon={LineChartIcon} tone="blue"/>
        </div>
        <p className="muted">{mlOutlook?.calibration_status || t("noValidatedModel")}</p>
      </article>

      <article className="card explanation-card"><div className="card-title"><FileText size={20}/><div><h3>{t("why")}</h3><p>Observed data, provider forecast, model output and historical baseline are kept distinct.</p></div></div>
        <div className="explanation-grid">
          <MiniMetric label={t("observedRain")} value={forecast?.explanation?.observed_recent_rainfall?.value_mm == null ? t("dataUnavailable") : `${forecast.explanation.observed_recent_rainfall.value_mm} mm · ${forecast.explanation.observed_recent_rainfall.days} days`}/>
          <MiniMetric label={t("historicalNormal")} value={forecast?.explanation?.historical_normal?.status || t("dataUnavailable")}/>
          <MiniMetric label={t("providerOnly")} value={amount(outlook?.expected_rainfall_mm)}/>
          <MiniMetric label={t("dryRisk")} value={percent(outlook?.dry_spell_probability)}/>
          <MiniMetric label={t("modelConfidence")} value={mlOutlook?.validated ? mlOutlook.calibration_status : t("noValidatedModel")}/>
        </div>
        <p className="muted">{t("climateContext")}: ENSO, IOD and MJO are observations only; no local coefficient is applied. Historical comparison needs local normals.</p>
        <details><summary>{t("dataTransparency")}</summary><p>{t("source")}: {forecast?.data_transparency?.data_source || t("dataUnavailable")} · {t("currentLocation")}: {forecast?.location?.label || t("dataUnavailable")}</p><p>{t("observedRain")}: {forecast?.data_transparency?.observation_timestamp || t("dataUnavailable")} · {t("forecastRetrieved")}: {formatDateTime(forecast?.data_transparency?.forecast_timestamp)}</p><p>{t("forecastHorizon")}: {horizon} days · {t("modelConfidence")}: {forecast?.data_transparency?.model_version || t("noMetric")} · {forecast?.data_transparency?.validated ? t("validatedYes") : t("validatedNo")}</p></details>
      </article>

      <article className="card">
        <div className="card-title"><LineChartIcon size={20}/><div><h3>{horizon}-day rainfall timeline</h3><p>Daily ensemble mean rainfall and member chance of at least 1 mm. Values update with the horizon selector.</p></div></div>
        {forecast?.daily?.length ? <div className="chart-body rainfall-chart"><ResponsiveContainer width="100%" height="100%"><LineChart data={forecast.daily.slice(0, Number(horizon))}><CartesianGrid strokeDasharray="3 3" stroke="#dfe7dd"/><XAxis dataKey="day" tickFormatter={(day) => `D${day}`} tickLine={false} axisLine={false}/><YAxis yAxisId="rain" tickLine={false} axisLine={false} label={{ value: "mm", angle: -90, position: "insideLeft" }}/><YAxis yAxisId="chance" orientation="right" domain={[0, 1]} tickFormatter={(v) => `${Math.round(v * 100)}%`} tickLine={false} axisLine={false}/><Tooltip labelFormatter={(day) => `Day ${day}`} formatter={(value, key) => [key === "rain_probability" ? `${Math.round(value * 100)}%` : `${value} mm`, key === "rain_probability" ? "Rain probability" : "Ensemble mean rainfall"]}/><Line yAxisId="rain" type="monotone" dataKey="expected_rainfall_mm" name="Ensemble mean rainfall" stroke="#2b713e" strokeWidth={3} dot={false}/><Line yAxisId="chance" type="monotone" dataKey="rain_probability" name="Rain probability" stroke="#d89022" strokeWidth={2} dot={false}/></LineChart></ResponsiveContainer></div> : <p className="muted">Daily rainfall outlook unavailable. Select a location or try again later.</p>}
      </article>

      <button className="secondary-button" type="button" onClick={() => setAdvancedView((value) => !value)}>{advancedView ? t("hideExpertView") : t("showExpertView")}</button>
      <div className="dashboard-grid">
        {advancedView && <article className="card climate-card">
          <div className="card-title"><Activity size={20}/><div><h3>Climate drivers</h3><p>Global signals are real index observations, not local rainfall predictions.</p></div></div>
          <div className="driver-grid">{(forecast?.climate_drivers?.drivers || []).map((driver) => <div className="driver-item" key={driver.name}><div><strong>{driver.name}</strong><span className={driver.value == null ? "driver-unavailable" : "driver-value"}>{driver.signal || "Data unavailable"}</span></div><p>{driver.impact || driver.error || "Index data unavailable."}</p><small>{driver.source || "Source unavailable"}{driver.observed_date ? ` · ${driver.observed_date}` : ""}</small></div>)}</div>
          <p className="muted">How these signals affect this location: no local climate-to-rainfall relationship has been validated or applied. They are shown for context only.</p>
        </article>}
        <article className="card history-card">
          <div className="card-title"><History size={20}/><div><h3>Recent rainfall context</h3><p>Gridded reanalysis; not a local rain-gauge reading.</p></div></div>
          {forecast?.recent_rainfall?.available ? <><p className="muted">{forecast.recent_rainfall.status} Source: {forecast.recent_rainfall.source}.</p><div className="recent-rain-strip">{forecast.recent_rainfall.daily.slice(-14).map((day) => <span key={day.date} title={`${day.date}: ${day.rainfall_mm ?? "unavailable"} mm`}><i style={{ height: `${Math.max(3, Math.min(48, (day.rainfall_mm || 0) * 2))}px` }}/><small>{day.date.slice(8)}</small></span>)}</div></> : <p className="muted">{forecast?.recent_rainfall?.status || "Data unavailable"}</p>}
        </article>
      </div>

      <article className="card sowing-card">
        <div className="card-title"><Sprout size={20}/><div><h3>Should I sow now?</h3><p>Decision support from the selected forecast window; not a guarantee or an official agricultural recommendation.</p></div></div>
        <div className="sowing-controls">
          <label>{t("cropName")}<input required value={decisionCropName} onChange={(event) => { setDecisionCropName(event.target.value); setDecision(null); }} /></label>
          <label>Crop stage<select value={decisionStage} onChange={(event) => setDecisionStage(event.target.value)}><option value="">{activeCrop ? t("dataUnavailable") : "Pre-sowing"}</option>{activeCrop?.growth_stage && <option value={activeCrop.growth_stage}>{translateCropStage(activeCrop.growth_stage, language)}</option>}</select></label>
          <label>Sowing preference<select value={sowingPreference} onChange={(event) => setSowingPreference(event.target.value)}><option>Sow as soon as conditions allow</option><option>Can wait one to two weeks</option><option>Must sow within this window</option></select></label>
          <label>Decision window<select value={decisionHorizon} onChange={(event) => setDecisionHorizon(Number(event.target.value))}>{[7, 14, 21, 30].map((days) => <option key={days} value={days}>{days} days</option>)}</select></label>
          <label className="checkbox-label"><input type="checkbox" checked={irrigation} onChange={(event) => setIrrigation(event.target.checked)}/>Irrigation available</label>
          <button className="primary-button" type="button" onClick={makeDecision} disabled={decisionLoading || forecastLocation.latitude == null || forecastLocation.longitude == null || !decisionCropName.trim()}>{decisionLoading ? "Checking outlook…" : t("reviewSowing")}</button>
        </div>
        {decisionError && <p className="form-error" role="status">{decisionError}</p>}
        {decision && <div className="decision-result" role="status"><span className={`decision-badge decision-${decision.decision?.toLowerCase().replaceAll(" ", "-")}`}>{decision.decision}</span><div><strong>{decision.confidence}</strong><p>{decision.reason}</p><p><b>Alternative:</b> {decision.alternative_action}</p></div></div>}
      </article>

      <article className="card advisory-panel">
        <div className="card-title"><Leaf size={20}/><div><h3>Recommended action</h3><p>Weather-informed prompts for the selected crop; confirm with field conditions and local extension advice.</p></div></div>
        <ul className="advisory-list">{(forecast?.advisory_details || []).map((item, index) => <li key={index}><strong>{localizedAdvice(item, language)}</strong><small>{localizedAdviceReason(item, language)}</small></li>)}</ul>
        {activeCrop && <p className="muted">Crop stage from AgriShield timeline: {activeCrop.growth_stage || "Not available"} · day {activeCrop.days_since_planting ?? "—"} since planting. Lifecycle-specific timing is a prompt and has not been locally validated.</p>}
      </article>
      <p className="muted source-note">{t("source")}: {forecast?.source?.name || t("dataUnavailable")}{forecast?.source?.generated_at ? ` · Retrieved ${formatDateTime(forecast.source.generated_at)}` : ""}. {t("noValidatedModel")}</p>
    </section>
  );
}

function SowingWindowPage({ crops, selectedCropId, location, language, onOpenLocation }) {
  const [cropName, setCropName] = useState("");
  const [assessment, setAssessment] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const t = (key) => mt(key, language);
  const selectedCrop = crops.find((crop) => String(crop.id) === String(selectedCropId));
  const assessmentLocation = selectedCrop?.latitude != null && selectedCrop?.longitude != null
    ? { ...location, latitude: selectedCrop.latitude, longitude: selectedCrop.longitude,
        location_id: selectedCrop.location_id, label: selectedCrop.location || location.label }
    : location;
  const hasAssessmentCoordinates = assessmentLocation.latitude != null && assessmentLocation.longitude != null;

  useEffect(() => {
    if (selectedCrop) setCropName(selectedCrop.crop_name);
  }, [selectedCrop?.id]);

  const assess = async (event) => {
    event.preventDefault();
    setError(""); setAssessment(null);
    if (!hasAssessmentCoordinates) { setError(t("selectLocation")); return; }
    if (!cropName.trim()) { setError(t("selectCrop")); return; }
    setLoading(true);
    try {
      const crop = crops.find((item) => item.crop_name.toLowerCase() === cropName.trim().toLowerCase());
      const payload = await getSowingWindow(assessmentLocation, cropName.trim(), crop?.id);
      setAssessment(payload.assessment);
    } catch (err) { setError(err.message); }
    finally { setLoading(false); }
  };

  useEffect(() => { setAssessment(null); }, [selectedCrop?.id, assessmentLocation.latitude, assessmentLocation.longitude]);

  return <section className="content-stack">
    <SectionHeader eyebrow={t("sowingWindow")} title={t("sowingWindow")} body={t("decisionSupport")} />
    <form className="card sowing-window-form" onSubmit={assess}>
      <div className="card-title"><Sprout size={20}/><div><h3>{t("sowingSuitability")}</h3><p>{t("suitabilityReason")}</p></div></div>
      <label className="field-label">{t("currentLocation")}<input readOnly value={assessmentLocation.label || ""} placeholder={t("chooseLocation")}/></label>
      <button className="secondary-button" type="button" onClick={onOpenLocation}>{t("search")}</button>
      <label className="field-label">{t("cropName")}<input required value={cropName} onChange={(event) => setCropName(event.target.value)} /></label>
      {error && <p role="status" className="form-error">{error}</p>}
      <button className="primary-button" type="submit" disabled={loading || !hasAssessmentCoordinates || !cropName.trim()}>{loading ? t("searching") : t("assessWindow")}</button>
    </form>
    {assessment && <article className="card assessment-result" role="status">
      <div className="card-title"><AlertCircle size={20}/><div><h3>{t("sowingSuitability")}: {t("unavailableSuitability")}</h3><p>{t("suitabilityReason")}</p></div></div>
      <p>{t("suitabilityReason")}</p>
      <ul>{assessment.reasons.map((reason) => <li key={reason}>{localizedSowingReason(reason, language)}</li>)}</ul>
      <div className="result-metrics">
        <MiniMetric label={t("expectedRain")} value={assessment.inputs.forecast_rainfall_mm_14d == null ? t("dataUnavailable") : `${assessment.inputs.forecast_rainfall_mm_14d} mm`} />
        <MiniMetric label={t("dryRisk")} value={assessment.inputs.dry_spell_member_frequency_14d == null ? t("dataUnavailable") : `${Math.round(assessment.inputs.dry_spell_member_frequency_14d * 100)}% raw GFS member frequency`} />
        <MiniMetric label={t("irrigation")} value={assessment.inputs.irrigation_type || t("dataUnavailable")} />
      </div>
      <p className="muted">{t("decisionSupport")}</p>
    </article>}
  </section>;
}

function AlertsPage({ location, language }) {
  const [payload, setPayload] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const t = (key) => mt(key, language);
  const refresh = async () => {
    setError(""); setPayload(null); setLoading(true);
    try { setPayload(await getMonsoonAlerts(location)); }
    catch (err) { setError(err.message); }
    finally { setLoading(false); }
  };
  useEffect(() => { refresh(); }, [location.latitude, location.longitude, location.location_id]);

  const acknowledge = async (alertId) => {
    try {
      await acknowledgeAlert(alertId);
      setPayload((current) => current ? { ...current, alerts: current.alerts.map((item) => item.id === alertId ? { ...item, status: "acknowledged" } : item) } : current);
    } catch (err) { setError(err.message); }
  };

  return <section className="content-stack">
    <SectionHeader eyebrow={t("alerts")} title={t("alerts")} body={t("decisionSupport")} action={<button className="secondary-button" type="button" onClick={refresh} disabled={loading}><RefreshCw size={16}/>{t("refresh")}</button>} />
    <article className="card"><p className="muted">{payload?.available ? t("alertThresholdNote") : loading ? t("searching") : t("selectLocation")}</p>
      {error && <p className="form-error" role="status">{error}</p>}
      {!loading && payload?.alerts?.length === 0 && <p>{payload?.available ? t("noAlerts") : t("forecastUnavailable")}</p>}
      <div className="alert-list">{(payload?.alerts || []).map((alert) => <article className={`in-app-alert severity-${alert.severity}`} key={alert.id}>
        <div><p className="eyebrow">{alert.alert_type === "dry_spell" ? t("dryAlertTitle") : alert.alert_type === "false_onset" ? t("falseOnsetAlertTitle") : t("heavyAlertTitle")}</p>
          <p>{alert.alert_type === "dry_spell" ? formatMt("dryAlertMessage", language, { percent: Math.round((alert.probability ?? 0) * 100), days: alert.horizon_days }) : alert.alert_type === "false_onset" ? formatMt("falseOnsetAlertMessage", language, { percent: Math.round((alert.probability ?? 0) * 100), days: alert.horizon_days }) : formatMt("heavyAlertMessage", language, { percent: Math.round((alert.probability ?? 0) * 100), days: alert.horizon_days })}</p>
          <small>{alert.source} · {alert.forecast_timestamp ? formatDateTime(alert.forecast_timestamp) : t("dataUnavailable")}</small>
        </div>
        {alert.status === "active" ? <button className="secondary-button" type="button" onClick={() => acknowledge(alert.id)}>{t("acknowledge")}</button> : <span className="status-pill">{t("acknowledged")}</span>}
      </article>)}</div>
    </article>
  </section>;
}

function ModelPerformancePage({ location, language }) {
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const t = (key) => mt(key, language);
  const refresh = async () => {
    setLoading(true); setError(""); setResult(null);
    try { setResult(await getModelPerformance(location.location_id)); }
    catch (err) { setError(err.message); }
    finally { setLoading(false); }
  };
  useEffect(() => { refresh(); }, [location.location_id]);
  const metricValue = (value, digits = 3) => value == null ? t("noMetric") : Number(value).toFixed(digits);
  const runs = result?.runs || [];

  return <section className="content-stack">
    <SectionHeader eyebrow={t("modelPerformance")} title={t("modelPerformance")} body={t("metricsNote")} action={<button className="secondary-button" type="button" onClick={refresh} disabled={loading}><RefreshCw size={16}/>{t("refresh")}</button>} />
    {error && <p className="form-error" role="status">{error}</p>}
    {!runs.length && <article className="card empty-state"><LineChartIcon size={34}/><h3>{t("noModels")}</h3><p>Import dated, location-specific observations and event labels before training. Forecast values from the weather provider do not count as AgriShield model validation.</p><code>python -m data.climate.ingest --input data/climate/observations.csv --location-id district:NAME:STATE --source station</code><code>python -m models.monsoon.training --location-id district:NAME:STATE</code></article>}
    {runs.map((run) => <article className="card model-run-card" key={run.model_version}>
      <div className="card-title"><Activity size={20}/><div><h3>{run.model_version}</h3><p>{run.algorithm} · {run.status} · n={run.sample_count} · data through {run.data_timestamp || t("dataUnavailable")}</p></div></div>
      <p>{t("metricsNote")} Test dates: {run.test_start || t("dataUnavailable")} – {run.test_end || t("dataUnavailable")}</p>
      <div className="metric-results">{Object.entries(run.metrics || {}).map(([key, metric]) => <article className="metric-result" key={key}>
        <h4>{localizedMetricName(key, language)}</h4><p>{localizedMetricStatus(metric.status, language)}</p>
        <div className="result-metrics">
          <MiniMetric label={t("precision")} value={metricValue(metric.precision)}/><MiniMetric label={t("recall")} value={metricValue(metric.recall)}/>
          <MiniMetric label={t("f1")} value={metricValue(metric.f1)}/><MiniMetric label={t("rocAuc")} value={metricValue(metric.roc_auc)}/>
          <MiniMetric label={t("brier")} value={metricValue(metric.brier_score)}/><MiniMetric label={t("mae")} value={metricValue(metric.mae, 2)}/>
          <MiniMetric label={t("rmse")} value={metricValue(metric.rmse, 2)}/><MiniMetric label="n test" value={metric.test_n}/>
        </div>
        {metric.calibration?.length > 0 && <p className="muted">Calibration diagnostics: {metric.calibration.filter((bin) => bin.n > 0).map((bin) => `${Math.round(bin.lower * 100)}–${Math.round(bin.upper * 100)}%: obs ${metricValue(bin.observed_frequency)} (n=${bin.n})`).join(" · ") || t("noMetric")}</p>}
      </article>)}</div>
      <p className="muted">Raw model probabilities are not calibrated unless a future calibration method is fitted. A held-out metric is a measurement, not a guarantee of future performance.</p>
    </article>)}
  </section>;
}

function localizedAdvice(item, language) {
  if (!item) return mt("dataUnavailable", language);
  const values = { crop: item.crop || "", stage: translateCropStage(item.stage || "pre-sowing", language) };
  if (item.type === "irrigation") return formatMt("irrigationAdvice", language, values);
  if (item.type === "drainage") return formatMt("drainageAdvice", language, values);
  if (item.type === "monitor") return formatMt("monitorAdvice", language, values);
  if (item.type === "fertilizer") return mt("fertilizerUnavailable", language);
  return language === "en" ? item.text : mt("forecastUnavailable", language);
}

function localizedSowingReason(reason, language) {
  const value = String(reason || "").toLowerCase();
  if (value.includes("weather forecast")) return mt("reasonWeatherMissing", language);
  if (value.includes("onset probability")) return mt("reasonOnsetMissing", language);
  if (value.includes("crop water requirement") || value.includes("crop calendar")) return mt("reasonCropCalendarMissing", language);
  if (value.includes("seasonal rainfall normals")) return mt("reasonNormalsMissing", language);
  if (value.includes("recent observed") || value.includes("reanalysis rainfall")) return mt("reasonRecentRainMissing", language);
  return reason;
}

function localizedMetricStatus(status, language) {
  const value = String(status || "").toLowerCase();
  if (value.includes("chronological held-out metrics computed")) return mt("metricComputed", language);
  if (value.includes("insufficient") || value.includes("needs both positive") || value.includes("lacks both event classes")) return mt("metricNotValidated", language);
  return status || mt("noMetric", language);
}

function localizedMetricName(key, language) {
  const [target, horizon] = String(key).split(":");
  const labels = {
    onset_event: mt("onset", language), false_onset_event: mt("falseOnset", language),
    dry_spell_event: mt("dryRisk", language), heavy_rain_event: mt("heavyRisk", language),
    rainfall_anomaly_mm: mt("anomaly", language),
  };
  return `${labels[target] || target.replaceAll("_", " ")} · ${horizon || ""} ${mt("forecastHorizon", language)}`;
}

function localizedAdviceReason(item, language) {
  if (item?.type === "irrigation") return formatMt("irrigationReason", language, { percent: item.percent ?? "" });
  if (item?.type === "drainage") return formatMt("drainageReason", language, { percent: item.percent ?? "" });
  if (item?.type === "monitor") return mt("monitorReason", language);
  if (item?.type === "fertilizer") return mt("fertilizerReason", language);
  return item?.reason || "";
}

function RiskBar({ label, value, language }) {
  const available = value != null;
  const tone = !available ? "" : value >= .67 ? " high" : value >= .34 ? " moderate" : " low";
  return <div className="risk-bar-row"><span>{label}</span><div className="risk-track" aria-hidden="true">{available && <i className={tone.trim()} style={{ width: `${Math.round(value * 100)}%` }}/>}</div><strong>{available ? `${Math.round(value * 100)}%` : mt("dataUnavailable", language)}</strong></div>;
}

function useLocationManager() {
  const readStoredLocation = () => {
    try { return JSON.parse(localStorage.getItem("agrishield-location") || "null"); }
    catch { return null; }
  };
  const [location, setLocation] = useState(() => readStoredLocation() || {
    label: "Choose a location", latitude: null, longitude: null, weather: null,
    status: "Location not selected", loading: false, error: "",
  });
  const latestSelection = useRef(0);

  const persistSelection = (selection) => {
    const normalized = {
      ...selection,
      label: selection.label || "Selected location",
      latitude: Number(selection.latitude), longitude: Number(selection.longitude),
      status: selection.status || "Location selected",
      weather: null, loading: false, error: "",
    };
    const selectionId = ++latestSelection.current;
    setLocation(normalized);
    localStorage.setItem("agrishield-location", JSON.stringify(normalized));
    saveLocation(normalized).catch(() => {
      if (selectionId === latestSelection.current) setLocation((current) => ({ ...current, status: "Location saved on this device; database sync unavailable" }));
    });
    getWeather(normalized.latitude, normalized.longitude).then((payload) => {
      if (selectionId !== latestSelection.current) return;
      const updated = { ...normalized, weather: payload.weather, status: payload.weather?.available ? `${normalized.status} · weather data available` : `${normalized.status} · weather data unavailable` };
      setLocation(updated);
      localStorage.setItem("agrishield-location", JSON.stringify(updated));
    }).catch(() => {
      if (selectionId === latestSelection.current) setLocation((current) => ({ ...current, status: `${normalized.status} · weather data unavailable` }));
    });
  };

  const select = (selection) => persistSelection({ ...selection,
    label: selection.label || [selection.name, selection.district, selection.state, selection.country].filter(Boolean).join(", "),
    status: selection.status || "Location selected from search",
  });

  const selectCoordinates = async (latitude, longitude, source = "GPS") => {
    const coordinates = { latitude: Number(latitude), longitude: Number(longitude) };
    setLocation((current) => ({ ...current, loading: true, error: "", status: source === "GPS" ? "GPS position found · resolving address" : "Resolving address" }));
    try {
      const payload = await reverseGeocode(coordinates.latitude, coordinates.longitude);
      persistSelection({ ...payload.location, ...coordinates, status: source === "GPS" ? "GPS location detected" : "Map coordinates selected" });
    } catch {
      persistSelection({ ...coordinates, label: source === "GPS" ? "GPS location · address lookup unavailable" : "Selected coordinates · address lookup unavailable", admin_level_available: "coordinates", source, status: `${source} location detected; administrative lookup unavailable` });
    }
  };

  const locate = () => {
    if (!("geolocation" in navigator)) {
      setLocation((current) => ({ ...current, error: "This device does not provide location access.", status: "Location unavailable" }));
      return;
    }
    setLocation((current) => ({ ...current, loading: true, error: "", status: "Requesting device location permission" }));
    navigator.geolocation.getCurrentPosition(
      (position) => selectCoordinates(position.coords.latitude, position.coords.longitude, "GPS"),
      (error) => setLocation((current) => ({ ...current, loading: false, error: error.code === 1 ? "Location permission was denied. Search for a village, town or district instead." : "Could not read device location. Search manually or try again.", status: "GPS location unavailable" })),
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 300000 },
    );
  };

  useEffect(() => {
    let active = true;
    const local = readStoredLocation();
    getSavedLocation().then(({ location: saved }) => {
      if (!active) return;
      const selected = local || saved;
      if (selected?.latitude != null && selected?.longitude != null) {
        setLocation({ ...selected, loading: false, error: "" });
        if (local && !saved) saveLocation(local).catch(() => {});
        getWeather(selected.latitude, selected.longitude).then((payload) => {
          if (active) setLocation((current) => ({ ...current, weather: payload.weather, status: payload.weather?.available ? "Saved location · weather data available" : "Saved location · weather data unavailable" }));
        }).catch(() => { if (active) setLocation((current) => ({ ...current, status: "Saved location · weather data unavailable" })); });
      }
    }).catch(() => {
      if (local?.latitude != null) setLocation({ ...local, loading: false });
    });
    return () => { active = false; };
  }, []);

  return { ...location, coordinates: location.latitude == null ? null : { latitude: location.latitude, longitude: location.longitude }, select, locate };
}

function Dashboard({ dashboard, crops, onCreateCrop, onQuickDiagnosis, onOpenCrop, onOpenMonsoon, weather, language }) {
  const summary = dashboard?.summary || {
    active_crops: 0,
    latest_health: "No scans yet",
    scans_recorded: 0,
  };
  const chartData = crops
    .filter((crop) => crop.scan_count > 0)
    .map((crop) => ({
      name: crop.field_name,
      scans: crop.scan_count,
    }));

  return (
    <section className="content-stack">
      <section className="dashboard-hero">
        <div>
          <p className="eyebrow">AgriShield</p>
          <h2>Plan around the weather ahead</h2>
          <p>
            Start with a location-specific monsoon outlook, then connect the weather risks to your crop lifecycle and health scans.
          </p>
          <div className="button-row">
            <button className="primary-button" type="button" onClick={onOpenMonsoon}><CloudRain size={18}/>Open Monsoon Intelligence</button>
            <button className="primary-button" type="button" onClick={onQuickDiagnosis}>
              <Search size={18} />
              Start diagnosis
            </button>
            <button className="secondary-button on-dark" type="button" onClick={onCreateCrop}>
              <Plus size={18} />
              Create crop
            </button>
          </div>
        </div>
      </section>

      <div className="metric-grid">
        <MetricCard title="Active crops" value={summary.active_crops} icon={Sprout} tone="green" />
        <MetricCard title="Latest health" value={summary.latest_health} icon={ShieldCheck} tone="emerald" />
        <MetricCard title="Scans recorded" value={summary.scans_recorded} icon={Camera} tone="amber" />
      </div>

        <WeatherMonitor weather={weather} language={language} />

      <div className="dashboard-grid">
        <article className="card">
          <div className="card-title">
            <Sprout size={20} />
            <div>
              <h3>Active Crop Profiles</h3>
              <p>Values come from the local SQLite database.</p>
            </div>
          </div>
          {crops.length ? (
            <div className="crop-card-grid">
              {crops.map((crop) => (
                <CropCard crop={crop} key={crop.id} onOpen={() => onOpenCrop(crop.id)} />
              ))}
            </div>
          ) : (
            <EmptyState
              icon={Sprout}
              title="No crop profiles yet"
              body="Create your first crop profile to start a persistent lifecycle record."
              actionLabel="Create crop profile"
              onAction={onCreateCrop}
            />
          )}
        </article>

        <article className="card">
          <div className="card-title">
            <Activity size={20} />
            <div>
              <h3>Recent Activity</h3>
              <p>Latest crop and scan events.</p>
            </div>
          </div>
          {dashboard?.recent_activity?.length ? (
            <div className="activity-list">
              {dashboard.recent_activity.map((item) => (
                <span key={`${item.type}-${item.date}-${item.title}`}>
                  <strong>{item.title}</strong>
                  <small>{item.detail} - {formatDateTime(item.date)}</small>
                </span>
              ))}
            </div>
          ) : (
            <p className="muted">No activity recorded yet.</p>
          )}
        </article>
      </div>

      <article className="card chart-card">
        <div className="card-title">
          <BarChart3 size={20} />
          <div>
            <h3>Scan History</h3>
            <p>Number of saved scans per crop profile.</p>
          </div>
        </div>
        {chartData.length ? (
          <div className="chart-body">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#dfe7dd" />
                <XAxis dataKey="name" tickLine={false} axisLine={false} />
                <YAxis allowDecimals={false} tickLine={false} axisLine={false} />
                <Tooltip />
                <Line type="monotone" dataKey="scans" stroke="#2b713e" strokeWidth={3} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <p className="muted">Add scans from a crop timeline to build the history graph.</p>
        )}
      </article>
    </section>
  );
}

function WeatherMonitor({ weather, language }) {
  const t = (key) => mt(key, language);
  return (
    <article className="card weather-monitor">
      <div className="card-title">
        <Activity size={20} />
        <div>
          <h3>{t("weatherMonitoring")}</h3>
          <p>{t("currentLocation")}: {weather?.source || t("dataUnavailable")}</p>
        </div>
      </div>
      {weather?.available ? (
        <>
          <div className="weather-grid">
            <MiniMetric label={t("temperature")} value={`${weather.temperature_c} C`} />
            <MiniMetric label={t("humidity")} value={`${weather.humidity_percent}%`} />
            <MiniMetric label={t("rainChance")} value={`${weather.rain_probability_percent}%`} />
            <MiniMetric label={t("diseaseWeatherRisk")} value={weather.risk_level} />
          </div>
          <p className="muted">{weather.advisory}</p>
        </>
      ) : (
        <p className="muted">{t("weatherUnavailable")}</p>
      )}
    </article>
  );
}

function CropCard({ crop, onOpen }) {
  return (
    <button className="crop-card" type="button" onClick={onOpen}>
      <div>
        <span className="pill">{crop.status}</span>
        <h3>{crop.crop_name}</h3>
        <p>{crop.field_name}</p>
      </div>
      <div className="crop-card-metrics">
        <MiniMetric label="Days since planting" value={crop.days_since_planting} />
        <MiniMetric label="Estimated stage" value={crop.growth_stage} />
        <MiniMetric label="Latest health" value={crop.latest_health_status} />
        <MiniMetric label="Scans" value={crop.scan_count} />
      </div>
      <div className="crop-card-footer">
        <span>Trend: {crop.health_trend}</span>
        <ChevronRight size={18} />
      </div>
    </button>
  );
}

function QuickDiagnosis({ language, location, onRefresh }) {
  const [cropName, setCropName] = useState("");
  const [description, setDescription] = useState("");
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const inputRef = useRef(null);

  const chooseFile = (selectedFile) => {
    setFile(selectedFile || null);
    setResult(null);
    if (!selectedFile) {
      setPreview("");
      return;
    }
    const reader = new FileReader();
    reader.onload = () => setPreview(String(reader.result || ""));
    reader.readAsDataURL(selectedFile);
  };

  const analyze = async (event) => {
    event.preventDefault();
    setError("");
    setResult(null);

    if (!cropName.trim()) {
      setError("Please enter the crop name.");
      return;
    }
    if (!file) {
      setError("Please upload a crop image.");
      return;
    }

    setLoading(true);
    try {
      const payload = await runQuickDiagnosis({
        crop_name: cropName,
        description,
        image: file,
        latitude: crop.latitude ?? location.latitude ?? location.coordinates?.latitude,
        longitude: crop.longitude ?? location.longitude ?? location.coordinates?.longitude,
      });
      setResult(payload.quick_diagnosis);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="content-stack">
      <SectionHeader
        eyebrow="Quick Diagnosis"
        title="Analyze a crop photo"
        body="The farmer supplies the crop name, and the trained disease model checks the uploaded image with crop-specific validation."
      />

      <div className="scan-layout">
        <form className="card upload-card" onSubmit={analyze}>
          <div className="card-title">
            <Microscope size={20} />
            <div>
              <h3>Crop health input</h3>
              <p>Uses the trained disease model with crop-specific validation.</p>
            </div>
          </div>

          <label className="field-label">
            What crop or plant is this?
            <input
              value={cropName}
              onChange={(event) => setCropName(event.target.value)}
              placeholder="Tomato, Potato, Maize, Apple, Grape..."
            />
            <small className="field-help">
              Best supported now: Tomato, Potato, Maize, Apple, Grape, Bell Pepper, Strawberry, Peach, Cherry, Orange, Soybean, Squash, Blueberry, Raspberry.
            </small>
          </label>

          <label className="field-label">
            What are you noticing? Optional
            <textarea
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              rows="5"
              placeholder="Black spots, yellow leaves, wilting, insects, when it started..."
            />
          </label>

          <input
            ref={inputRef}
            className="hidden-input"
            type="file"
            accept="image/*"
            onChange={(event) => chooseFile(event.target.files?.[0])}
          />
          <button className={`dropzone ${preview ? "has-preview" : ""}`} type="button" onClick={() => inputRef.current?.click()}>
            {preview ? (
              <img src={preview} alt="Selected crop preview" />
            ) : (
              <span>
                <Upload size={34} />
                <strong>Upload crop image</strong>
                <small>Use a clear photo of the affected plant part.</small>
              </span>
            )}
          </button>

          {error && <p className="form-error">{error}</p>}

          <button className="primary-button full-width" type="submit" disabled={loading}>
            {loading ? <Loader2 className="spin" size={18} /> : <Search size={18} />}
            {loading ? "Analyzing crop health..." : "Analyze Crop Health"}
          </button>
        </form>

        <div className="result-column">
          {loading ? (
            <AnalysisProgress />
          ) : result ? (
            <QuickResult result={result} language={language} />
          ) : (
            <EmptyState
              icon={ImagePlus}
              title="Your assessment will appear here"
              body="After upload, AgriShield stores the image, runs analysis, and shows remedies, precautions, and next checks."
            />
          )}
        </div>
      </div>
    </section>
  );
}

function QuickResult({ result, language }) {
  return (
    <article className="card result-card">
      <div className="success-banner">
        <CheckCircle2 size={18} />
        <span>Analysis complete. Review the diagnosis, remedies, precautions, and next check below.</span>
      </div>
      <div className="result-header">
        <div>
          <p className="eyebrow">{result.crop_name}</p>
          <h2>{result.diagnosis}</h2>
        </div>
        <span className="status-pill pending">{result.reliability}</span>
      </div>
      {result.image_url && <img className="result-image" src={imageUrl(result.image_url)} alt="Uploaded crop" />}
      <div className="result-metrics">
        <MiniMetric label={tr("Diagnosis", language)} value={result.diagnosis} />
        <MiniMetric label="Health Status" value={result.health_status} />
        <MiniMetric label={tr("Reliability", language)} value={result.reliability} />
      </div>
      <InfoBlock title={tr("Recommended Actions", language)} items={result.recommendations} />
      <InfoBlock title={tr("Medicine Guidance", language)} items={result.medicine_guidance} />
      <InfoBlock title={tr("Fertilizer Guidance", language)} items={result.fertilizer_guidance} />
      <InfoBlock title={tr("Natural Remedies", language)} items={result.natural_remedies} />
      <InfoBlock title={tr("Precautions", language)} items={result.precautions} />
      {result.weather?.available && <InfoBlock title="Weather Monitoring" body={result.weather.advisory} />}
      <InfoBlock title={tr("Next Check", language)} items={result.next_check} />
      <InfoBlock title={tr("Do Not", language)} items={result.do_not} />
    </article>
  );
}

function MyCrop({ crops, location, language, onCreated, onRefresh, onArchived, onOpenTimeline, onOpenLocation }) {
  const [form, setForm] = useState(() => {
    try { return JSON.parse(sessionStorage.getItem("agrishield-crop-draft")) || freshCropForm(); }
    catch { return freshCropForm(); }
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [editingId, setEditingId] = useState(() => sessionStorage.getItem("agrishield-editing-crop-id") || null);
  const [locationChanged, setLocationChanged] = useState(() => sessionStorage.getItem("agrishield-crop-location-changed") === "true");
  const t = (key) => mt(key, language);
  const editingCrop = crops.find((crop) => String(crop.id) === String(editingId));
  const displayedLocation = editingId && !locationChanged ? editingCrop?.location : location.label;

  const clearDraft = () => {
    sessionStorage.removeItem("agrishield-crop-draft");
    sessionStorage.removeItem("agrishield-editing-crop-id");
    sessionStorage.removeItem("agrishield-crop-location-changed");
    setEditingId(null);
    setLocationChanged(false);
    setForm(freshCropForm());
  };

  const update = (key, value) => setForm((current) => {
    const next = { ...current, [key]: value };
    sessionStorage.setItem("agrishield-crop-draft", JSON.stringify(next));
    return next;
  });

  const submit = async (event) => {
    event.preventDefault();
    setError("");
    const savedEditingCrop = crops.find((crop) => String(crop.id) === String(editingId));
    const missingSavedFieldLocation = Boolean(editingId && !locationChanged &&
      (savedEditingCrop?.latitude == null || savedEditingCrop?.longitude == null));
    if (missingSavedFieldLocation || (locationChanged && !location.coordinates) || (!editingId && !location.coordinates)) {
      setError(t("selectLocation"));
      return;
    }
    setLoading(true);
    try {
      const existingCrop = savedEditingCrop;
      const fieldLocation = editingId && !locationChanged ? existingCrop : location;
      const cropPayload = {
        ...form,
        latitude: fieldLocation.latitude,
        longitude: fieldLocation.longitude,
        location: locationChanged ? (location.label || "") : (existingCrop?.location || form.location || location.label || ""),
        state: fieldLocation.state,
        district: fieldLocation.district,
        block: fieldLocation.block,
        village_cluster: fieldLocation.village_cluster || fieldLocation.village,
        location_id: fieldLocation.location_id,
      };
      const payload = editingId ? await updateCrop(editingId, cropPayload) : await createCrop(cropPayload);
      clearDraft();
      if (editingId) {
        await onRefresh(String(payload.crop.id));
      } else onCreated(payload.crop);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="content-stack">
      <SectionHeader
        eyebrow="My Crop"
        title="Create a living crop profile"
        body="Each crop profile is saved to SQLite and can hold repeated scans throughout the season."
      />

      <div className="two-column">
        <form className="card" onSubmit={submit}>
          <div className="card-title">
            <ClipboardList size={20} />
            <div>
              <h3>{editingId ? t("edit") : t("cropName")}</h3>
              <p>Crop → location → sowing date → field area → irrigation → confirmation.</p>
            </div>
          </div>

          <label className="field-label">
            {t("cropName")}
            <input required value={form.crop_name} onChange={(event) => update("crop_name", event.target.value)} placeholder="" />
          </label>
          <label className="field-label">
            {t("fieldName")}
            <input required value={form.field_name} onChange={(event) => update("field_name", event.target.value)} placeholder="" />
          </label>
          <label className="field-label">
            {t("currentLocation")}
            <input readOnly value={displayedLocation || ""} placeholder={t("chooseLocation")} />
          </label>
          <button className="secondary-button" type="button" onClick={() => {
            sessionStorage.setItem("agrishield-crop-draft", JSON.stringify(form));
            if (editingId) sessionStorage.setItem("agrishield-editing-crop-id", String(editingId));
            sessionStorage.setItem("agrishield-crop-location-changed", "true");
            setLocationChanged(true);
            onOpenLocation();
          }}>{t("search")}</button>
          <label className="field-label">
            {t("sowingDate")}
            <input required type="date" value={form.planting_date} onChange={(event) => update("planting_date", event.target.value)} />
          </label>
          <div className="sowing-controls">
            <label className="field-label">
              {t("fieldArea")}
              <input required type="number" min="0.01" step="any" value={form.field_area} onChange={(event) => update("field_area", event.target.value)} />
            </label>
            <label className="field-label">
              {t("areaUnit")}
              <select value={form.field_area_unit} onChange={(event) => update("field_area_unit", event.target.value)}>
                <option value="acre">{t("acre")}</option><option value="hectare">{t("hectare")}</option><option value="square_metre">{t("squareMetre")}</option>
              </select>
            </label>
          </div>
          <label className="field-label">
            {t("irrigation")}
            <select required value={form.irrigation_type} onChange={(event) => update("irrigation_type", event.target.value)}>
              <option value="">{t("selectIrrigation")}</option><option value="rainfed">{t("rainfed")}</option><option value="canal">{t("canal")}</option>
              <option value="drip">{t("drip")}</option><option value="sprinkler">{t("sprinkler")}</option><option value="borewell">{t("borewell")}</option><option value="other">{t("other")}</option>
            </select>
          </label>
          <label className="field-label">
            Notes optional
            <textarea value={form.notes} onChange={(event) => update("notes", event.target.value)} rows="4" placeholder="Variety, irrigation pattern, soil notes..." />
          </label>

          {error && <p className="form-error">{error}</p>}

          <button className="primary-button full-width" type="submit" disabled={loading}>
            {loading ? <Loader2 className="spin" size={18} /> : <Plus size={18} />}
            {loading ? "Saving…" : editingId ? t("confirmCrop") : t("createCrop")}
          </button>
          {editingId && <button className="secondary-button full-width" type="button" onClick={() => { clearDraft(); setError(""); }}>{t("cancel")}</button>}
        </form>

        <article className="card">
          <div className="card-title">
            <Sprout size={20} />
            <div>
              <h3>Saved crop profiles</h3>
              <p>Real records from the local database.</p>
            </div>
          </div>
          {crops.length ? (
            <div className="activity-list">
              {crops.map((crop) => (
                <div className="saved-crop-item" key={crop.id}>
                  <button className="saved-crop-row" type="button" onClick={() => onOpenTimeline(crop.id)}>
                    <span>
                      <strong>{crop.crop_name} - {crop.field_name}</strong>
                      <small>{crop.status === "planned" ? "Planned · " : "Sown · "}{formatDate(crop.planting_date)} - {crop.scan_count} scans - {translateCropStage(crop.growth_stage, language)}</small>
                    </span>
                    <ChevronRight size={18} />
                  </button>
                  <div className="button-row">
                    <button className="secondary-button" type="button" onClick={() => {
                      setEditingId(crop.id);
                      sessionStorage.setItem("agrishield-editing-crop-id", String(crop.id));
                      sessionStorage.removeItem("agrishield-crop-location-changed");
                      setLocationChanged(false);
                      setForm({ crop_name: crop.crop_name, field_name: crop.field_name, planting_date: crop.planting_date,
                        location: crop.location || "", field_area: crop.field_area ?? "", field_area_unit: crop.field_area_unit || "acre",
                        irrigation_type: crop.irrigation_type || "", notes: crop.notes || "" });
                      setError("");
                    }}>{t("edit")}</button>
                    <button className="secondary-button" type="button" onClick={async () => {
                      if (!window.confirm(formatMt("archiveConfirm", language, { crop: crop.crop_name, field: crop.field_name }))) return;
                      try {
                        await archiveCrop(crop.id);
                        if (String(editingId) === String(crop.id)) clearDraft();
                        await onArchived(crop.id);
                      }
                      catch (err) { setError(err.message); }
                    }}>{t("archive")}</button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="muted">No crop profiles have been created yet.</p>
          )}
        </article>
      </div>
    </section>
  );
}

function CropTimeline({ crops, selectedCropId, selectedCrop, setSelectedCropId, onScanCreated, openCropPage, language, location }) {
  const [showForm, setShowForm] = useState(false);
  const [timelineForecast, setTimelineForecast] = useState(null);
  const [timelineForecastLoading, setTimelineForecastLoading] = useState(false);
  useEffect(() => {
    if (!selectedCropId) { setTimelineForecast(null); return undefined; }
    let active = true;
    setTimelineForecastLoading(true);
    setTimelineForecast(null);
    const cropLocation = selectedCrop?.latitude != null && selectedCrop?.longitude != null
      ? { ...location, latitude: selectedCrop.latitude, longitude: selectedCrop.longitude,
          location_id: selectedCrop.location_id, label: selectedCrop.location }
      : location;
    getMonsoonForecast(cropLocation, selectedCropId)
      .then((payload) => { if (active) setTimelineForecast(payload.forecast); })
      .catch(() => { if (active) setTimelineForecast(null); })
      .finally(() => { if (active) setTimelineForecastLoading(false); });
    return () => { active = false; };
  }, [selectedCropId, selectedCrop?.latitude, selectedCrop?.longitude, selectedCrop?.location_id, location.latitude, location.longitude]);
  const scans = selectedCrop?.scans || [];
  const chartData = scans.map((scan) => ({
    name: `Day ${scan.day_number}`,
    scans: 1,
    health: scan.health_score,
  }));
  const timelineWeek = timelineForecast?.horizons?.find((item) => item.days === 7);
  const timelineModelWeek = timelineForecast?.agri_model?.horizons?.["7"];
  const timelineDryRisk = timelineModelWeek?.validated
    ? timelineModelWeek.predictions?.dry_spell_event ?? timelineWeek?.dry_spell_probability
    : timelineWeek?.dry_spell_probability;
  const timelineHeavyRisk = timelineModelWeek?.validated
    ? timelineModelWeek.predictions?.heavy_rain_event ?? timelineWeek?.heavy_rain_probability
    : timelineWeek?.heavy_rain_probability;

  if (!crops.length) {
    return (
      <EmptyState
        icon={Sprout}
        title="Create a crop first"
        body="A timeline belongs to a real crop profile, so create one before adding scans."
        actionLabel="Create crop profile"
        onAction={openCropPage}
      />
    );
  }

  return (
    <section className="content-stack">
      <SectionHeader
        eyebrow="Crop Timeline"
        title={selectedCrop ? `${selectedCrop.crop_name} - ${selectedCrop.field_name}` : "Crop timeline"}
        body="Every scan is stored against this crop and displayed chronologically."
        action={
          <select className="plain-select" value={selectedCropId} onChange={(event) => setSelectedCropId(event.target.value)}>
            {crops.map((crop) => (
              <option key={crop.id} value={crop.id}>
                {crop.crop_name} - {crop.field_name}
              </option>
            ))}
          </select>
        }
      />

      {selectedCrop && (
        <>
          <div className="card timeline-monsoon">
            <div className="card-title"><CloudRain size={20}/><div><h3>Monsoon outlook for this crop</h3><p>{timelineForecastLoading ? "Loading location-specific weather ensemble…" : timelineForecast?.data_status || "Weather data unavailable for the saved location."}</p></div></div>
            <div className="horizon-row">{(timelineForecast?.horizons || []).map((item) => <span className="horizon-chip" key={item.days}>{item.days} days · {item.expected_rainfall_mm == null ? "unavailable" : `${item.expected_rainfall_mm} mm`} · {item.rainfall_probability == null ? "probability unavailable" : `${Math.round(item.rainfall_probability * 100)}% rain chance`}</span>)}</div>
            <div className="risk-list"><RiskBar language={language} label={mt("dryRisk", language)} value={timelineDryRisk}/><RiskBar language={language} label={mt("heavyRisk", language)} value={timelineHeavyRisk}/></div>
            <ul className="advisory-list">{timelineForecast?.advisory_details?.length ? timelineForecast.advisory_details.map((item, index) => <li key={index}><strong>{localizedAdvice(item, language)}</strong><small>{localizedAdviceReason(item, language)}</small></li>) : (timelineForecast?.advisory || [mt("forecastUnavailable", language)]).map((item, index) => <li key={index}>{item}</li>)}</ul>
          </div>
          <div className="metric-grid">
            <MetricCard title="Days since sowing" value={selectedCrop.days_since_planting == null ? mt("stageNotPlanted", language) : selectedCrop.days_since_planting} icon={CalendarDays} tone="green" />
            <MetricCard title="Estimated growth stage" value={translateCropStage(selectedCrop.growth_stage, language)} icon={Leaf} tone="emerald" />
            <MetricCard title="Latest health" value={selectedCrop.latest_health_status} icon={ShieldCheck} tone="amber" />
            <MetricCard title="Health trend" value={selectedCrop.health_trend} icon={LineChartIcon} tone="red" />
          </div>

          <article className="card crop-summary-card">
            <div>
              <p className="eyebrow">Profile details</p>
              <h3>{selectedCrop.crop_name}</h3>
              <p className="muted">
                {selectedCrop.field_name} - {selectedCrop.status === "planned" ? "planned sowing" : "sown"} {formatDate(selectedCrop.planting_date)}
                {selectedCrop.location ? ` - ${selectedCrop.location}` : ""}
              </p>
              {selectedCrop.field_area != null && <p className="muted">Field area: {selectedCrop.field_area} {selectedCrop.field_area_unit} · irrigation: {selectedCrop.irrigation_type || "Not recorded"}</p>}
              {selectedCrop.next_stage && <p className="muted">Next lifecycle stage: {translateCropStage(selectedCrop.next_stage, language)}{selectedCrop.days_to_next_stage != null ? ` · about ${selectedCrop.days_to_next_stage} days` : ""}. {selectedCrop.lifecycle_source}</p>}
              {selectedCrop.crop_calendar && <p className="muted">Imported local crop calendar: {selectedCrop.crop_calendar.source}{selectedCrop.crop_calendar.sowing_start && selectedCrop.crop_calendar.sowing_end ? ` · sowing window ${selectedCrop.crop_calendar.sowing_start}–${selectedCrop.crop_calendar.sowing_end}` : ""}. Forecast values remain weather-grid guidance.</p>}
              {selectedCrop.status === "planned" && <p className="data-banner">Pre-sowing state: age and active growth stage have not started.</p>}
              {selectedCrop.notes && <p>{selectedCrop.notes}</p>}
            </div>
            <button className="primary-button" type="button" onClick={() => setShowForm((value) => !value)}>
              <Plus size={18} />
              Add New Scan
            </button>
          </article>

          {showForm && (
            <AddScanForm
              crop={selectedCrop}
              location={{ ...location, latitude: selectedCrop?.latitude ?? location.latitude,
                longitude: selectedCrop?.longitude ?? location.longitude }}
              onSaved={(crop) => {
                setShowForm(false);
                onScanCreated(crop);
              }}
            />
          )}

          <div className="dashboard-grid">
            <article className="card chart-card">
              <div className="card-title">
                <BarChart3 size={20} />
                <div>
                  <h3>Health History</h3>
                  <p>Built from saved scans for this crop.</p>
                </div>
              </div>
              {chartData.length ? (
                <div className="chart-body">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={chartData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#dfe7dd" />
                      <XAxis dataKey="name" tickLine={false} axisLine={false} />
                      <YAxis allowDecimals={false} tickLine={false} axisLine={false} />
                      <Tooltip />
                      <Line type="monotone" dataKey="scans" name="Scan recorded" stroke="#2b713e" strokeWidth={3} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <p className="muted">No scans yet. Add a scan to begin the timeline.</p>
              )}
            </article>

            <article className="card">
              <div className="card-title">
                <Clock3 size={20} />
                <div>
                  <h3>Comparison Readiness</h3>
                  <p>Previous-scan structure is ready for diagnosis later.</p>
                </div>
              </div>
              <div className="readiness-list">
                <span className={scans.length >= 1 ? "ready" : ""}>
                  <CheckCircle2 size={17} />
                  First scan saved
                </span>
                <span className={scans.length >= 2 ? "ready" : ""}>
                  <CheckCircle2 size={17} />
                  Previous scan available
                </span>
                <span>
                  <AlertTriangle size={17} />
                  Disease comparison uses saved analysis results
                </span>
              </div>
            </article>
          </div>

          <article className="card">
            <div className="card-title">
              <History size={20} />
              <div>
                <h3>Scan History</h3>
                <p>Chronological scan records for this crop.</p>
              </div>
            </div>
            {scans.length ? (
              <div className="timeline">
                {scans.map((scan) => (
                  <ScanCard crop={selectedCrop} scan={scan} key={scan.id} language={language} />
                ))}
              </div>
            ) : (
              <EmptyState
                icon={Camera}
                title="No scans saved yet"
                body="Use Add New Scan to store the first photo, date, description, and pending diagnosis record."
              />
            )}
          </article>
        </>
      )}
    </section>
  );
}

function AddScanForm({ crop, location, onSaved }) {
  const [scanDate, setScanDate] = useState(todayISO());
  const [description, setDescription] = useState("");
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const inputRef = useRef(null);

  const chooseFile = (selectedFile) => {
    setFile(selectedFile || null);
    if (!selectedFile) {
      setPreview("");
      return;
    }
    const reader = new FileReader();
    reader.onload = () => setPreview(String(reader.result || ""));
    reader.readAsDataURL(selectedFile);
  };

  const submit = async (event) => {
    event.preventDefault();
    setError("");
    if (!file) {
      setError("Please upload a scan image.");
      return;
    }
    setLoading(true);
    try {
      const payload = await createTimelineScan(crop.id, {
        scan_date: scanDate,
        description,
        image: file,
        latitude: location.coordinates?.latitude,
        longitude: location.coordinates?.longitude,
      });
      onSaved(payload.crop);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <form className="card add-scan-card" onSubmit={submit}>
      <div className="card-title">
        <Camera size={20} />
        <div>
          <h3>Add scan for {crop.crop_name}</h3>
          <p>Crop is selected automatically from the timeline.</p>
        </div>
      </div>
      <div className="scan-form-grid">
        <label className="field-label">
          Scan date
          <input type="date" value={scanDate} onChange={(event) => setScanDate(event.target.value)} />
        </label>
        <label className="field-label wide">
          Optional description
          <textarea value={description} onChange={(event) => setDescription(event.target.value)} rows="3" placeholder="What changed since the previous scan?" />
        </label>
      </div>
      <input
        ref={inputRef}
        className="hidden-input"
        type="file"
        accept="image/*"
        onChange={(event) => chooseFile(event.target.files?.[0])}
      />
      <button className={`dropzone compact ${preview ? "has-preview" : ""}`} type="button" onClick={() => inputRef.current?.click()}>
        {preview ? (
          <img src={preview} alt="Scan preview" />
        ) : (
          <span>
            <Upload size={30} />
            <strong>Upload scan image</strong>
            <small>Image will be saved in the uploads folder.</small>
          </span>
        )}
      </button>
      {error && <p className="form-error">{error}</p>}
      <button className="primary-button" type="submit" disabled={loading}>
        {loading ? <Loader2 className="spin" size={18} /> : <Plus size={18} />}
        {loading ? "Analyzing scan..." : "Analyze Scan"}
      </button>
      {loading && (
        <p className="muted analysis-note">
          Running disease analysis and saving remedies. The first scan can take a few seconds.
        </p>
      )}
    </form>
  );
}

function ScanCard({ crop, scan, language }) {
  const [expanded, setExpanded] = useState(false);
  const [comparison, setComparison] = useState(null);
  const [loadingCompare, setLoadingCompare] = useState(false);
  const [error, setError] = useState("");

  const loadComparison = async () => {
    setError("");
    setLoadingCompare(true);
    try {
      const payload = await compareScan(scan.id);
      setComparison(payload);
      setExpanded(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoadingCompare(false);
    }
  };

  return (
    <article className="timeline-item">
      <div className="timeline-dot" />
      <div className="timeline-content">
        <div className="timeline-head">
          <div>
            <span className="pill">Day {scan.day_number}</span>
            <h3>{formatDate(scan.scan_date)}</h3>
            <p>{scan.growth_stage}</p>
          </div>
          <span className="status-pill pending">{scan.health_status}</span>
        </div>

        <div className="scan-detail-grid">
          <img className="scan-thumb" src={imageUrl(scan.image_url)} alt={`${crop.crop_name} scan`} />
          <div>
            <div className="result-metrics">
              <MiniMetric label={tr("Diagnosis", language)} value={scan.diagnosis} />
              <MiniMetric label={tr("Reliability", language)} value={scan.reliability} />
              <MiniMetric label={tr("Severity", language)} value={scan.severity === "Unknown" ? "Cannot be reliably estimated" : scan.severity} />
            </div>
          </div>
        </div>

        <div className="button-row">
          <button className="secondary-button" type="button" onClick={() => setExpanded((value) => !value)}>
            <FileText size={18} />
            {expanded ? "Hide scan details" : "Open scan details"}
          </button>
          <button className="secondary-button" type="button" onClick={loadComparison} disabled={loadingCompare}>
            {loadingCompare ? <Loader2 className="spin" size={18} /> : <LineChartIcon size={18} />}
            Compare with previous scan
          </button>
        </div>

        {error && <p className="form-error">{error}</p>}

        {expanded && (
          <div className="scan-expanded">
            <InfoBlock title={tr("Recommended Actions", language)} items={scan.recommendations} />
            <InfoBlock title={tr("Medicine Guidance", language)} items={scan.medicine_guidance} />
            <InfoBlock title={tr("Fertilizer Guidance", language)} items={scan.fertilizer_guidance} />
            <InfoBlock title={tr("Natural Remedies", language)} items={scan.natural_remedies} />
            <InfoBlock title={tr("Precautions", language)} items={scan.precautions} />
            <InfoBlock title={tr("Do Not", language)} items={scan.do_not} />
            <InfoBlock title={tr("Next Check", language)} items={scan.next_check} />
            <InfoBlock title="Follow Up" body={scan.follow_up} />
            <InfoBlock title="Expert Confirmation" body={scan.expert_confirmation} />
          </div>
        )}

        {comparison && <ComparisonPanel comparison={comparison} />}
      </div>
    </article>
  );
}

function ComparisonPanel({ comparison }) {
  const previous = comparison.previous_scan;
  const current = comparison.current_scan;

  return (
    <div className="comparison-panel">
      <div className="card-title">
        <LineChartIcon size={20} />
        <div>
          <h3>Previous Scan Comparison</h3>
          <p>{comparison.explanation}</p>
        </div>
      </div>
      {previous ? (
        <div className="compare-grid">
          <CompareScan title="Previous scan" scan={previous} />
          <CompareScan title="Current scan" scan={current} />
        </div>
      ) : (
        <p className="muted">Insufficient data for a reliable progression assessment.</p>
      )}
      <div className="result-metrics">
        <MiniMetric label="Health trend" value={comparison.health_trend} />
        <MiniMetric label="Previous severity" value={previous?.severity || "No previous scan"} />
        <MiniMetric label="Current severity" value={current?.severity || "Unknown"} />
      </div>
    </div>
  );
}

function CompareScan({ title, scan }) {
  return (
    <div className="compare-card">
      <h4>{title}</h4>
      <img src={imageUrl(scan.image_url)} alt={title} />
      <strong>{scan.diagnosis}</strong>
      <small>
        {formatDate(scan.scan_date)} - {scan.severity}
      </small>
    </div>
  );
}

function SectionHeader({ eyebrow, title, body, action }) {
  return (
    <div className="section-header">
      <div>
        <p className="eyebrow">{eyebrow}</p>
        <h2>{title}</h2>
        {body && <p>{body}</p>}
      </div>
      {action && <div className="section-action">{action}</div>}
    </div>
  );
}

function MetricCard({ title, value, icon: Icon, tone }) {
  return (
    <article className={`metric-card tone-${tone}`}>
      <span className="metric-icon">
        <Icon size={22} />
      </span>
      <div>
        <p>{title}</p>
        <strong>{value}</strong>
      </div>
    </article>
  );
}

function MiniMetric({ label, value }) {
  return (
    <span className="mini-metric">
      <small>{label}</small>
      <strong>{value ?? "Not recorded"}</strong>
    </span>
  );
}

function InfoBlock({ title, body, items }) {
  if (!body && !items?.length) return null;
  return (
    <div className="info-block">
      <h4>{title}</h4>
      {body && <p>{body}</p>}
      {items?.length > 0 && (
        <ul>
          {items.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

function EmptyState({ title, body, icon: Icon, actionLabel, onAction }) {
  return (
    <article className="card empty-state">
      <Icon size={34} />
      <h3>{title}</h3>
      <p>{body}</p>
      {actionLabel && (
        <button className="primary-button" type="button" onClick={onAction}>
          <Plus size={18} />
          {actionLabel}
        </button>
      )}
    </article>
  );
}

function AnalysisProgress() {
  return (
    <article className="card empty-state loading-state analysis-progress">
      <Loader2 className="spin" size={34} />
      <h3>Analyzing crop health</h3>
      <p>Checking the image with the disease model and preparing remedies, precautions, fertilizer guidance, and weather-aware advice.</p>
    </article>
  );
}

function LoadingState() {
  return (
    <article className="card empty-state loading-state">
      <Loader2 className="spin" size={34} />
      <h3>Loading AgriShield</h3>
      <p>Reading crop profiles and scan records from SQLite.</p>
    </article>
  );
}

export default App;
