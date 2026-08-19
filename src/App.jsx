import React, { useEffect, useMemo, useRef, useState } from "react";
import {
  Activity,
  AlertTriangle,
  BarChart3,
  CalendarDays,
  Camera,
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
} from "./services/aiApi";

const navItems = [
  { id: "dashboard", label: "Dashboard", icon: Home },
  { id: "quick", label: "Quick Diagnosis", icon: Microscope },
  { id: "crop", label: "My Crop", icon: Sprout },
  { id: "timeline", label: "Crop Timeline", icon: History },
];

const languageOptions = [
  { code: "en", label: "English" },
  { code: "hi", label: "Hindi" },
  { code: "te", label: "Telugu" },
  { code: "ta", label: "Tamil" },
  { code: "kn", label: "Kannada" },
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
    planting_date: localDateISO(),
    location: "",
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
  const [page, setPage] = useState("dashboard");
  const [dashboard, setDashboard] = useState(null);
  const [crops, setCrops] = useState([]);
  const [selectedCropId, setSelectedCropId] = useState("");
  const [selectedCrop, setSelectedCrop] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [refreshKey, setRefreshKey] = useState(0);
  const [language, setLanguage] = useState("en");
  const location = useLocationHint();

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
          onCreated={handleCropCreated}
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
            <small>Crop health monitor</small>
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
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>
      </aside>

      <main className="main-panel">
        <header className="topbar">
          <div>
            <p className="eyebrow">Crop lifecycle command center</p>
            <h1>{navItems.find((item) => item.id === page)?.label || "Dashboard"}</h1>
          </div>
          <div className="topbar-actions">
            <button className="icon-button" type="button" onClick={reload} aria-label="Refresh data">
              <RefreshCw size={18} />
            </button>
            <div className="environment-chip">
              <MapPin size={16} />
              <span>{location.label}</span>
            </div>
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
              <select value={language} onChange={(event) => setLanguage(event.target.value)} aria-label="Translate result labels">
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

function useLocationHint() {
  const [location, setLocation] = useState({
    label: "Location permission optional",
    coordinates: null,
    weather: null,
  });

  useEffect(() => {
    let active = true;
    if (!("geolocation" in navigator)) {
      setLocation((current) => ({ ...current, label: "Location not available" }));
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (position) => {
        const coordinates = {
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
        };
        const lat = coordinates.latitude.toFixed(4);
        const lng = coordinates.longitude.toFixed(4);
        setLocation({ label: `${lat}, ${lng}`, coordinates, weather: null });
        getWeather(coordinates.latitude, coordinates.longitude)
          .then((payload) => {
            if (active) {
              setLocation({ label: `${lat}, ${lng}`, coordinates, weather: payload.weather });
            }
          })
          .catch(() => {
            if (active) {
              setLocation({ label: `${lat}, ${lng}`, coordinates, weather: null });
            }
          });
      },
      () => setLocation((current) => ({ ...current, label: "Location not shared" })),
      { enableHighAccuracy: true, timeout: 7000, maximumAge: 300000 },
    );
    return () => {
      active = false;
    };
  }, []);

  return location;
}

function Dashboard({ dashboard, crops, onCreateCrop, onQuickDiagnosis, onOpenCrop, weather }) {
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
          <h2>Your crop health at a glance</h2>
          <p>
            Create real crop profiles, save repeated scans, and follow each crop from planting
            through its lifecycle.
          </p>
          <div className="button-row">
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

      <WeatherMonitor weather={weather} />

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

function WeatherMonitor({ weather }) {
  return (
    <article className="card weather-monitor">
      <div className="card-title">
        <Activity size={20} />
        <div>
          <h3>Weather Based Monitoring</h3>
          <p>Uses your shared location to estimate rain and humidity disease pressure.</p>
        </div>
      </div>
      {weather?.available ? (
        <>
          <div className="weather-grid">
            <MiniMetric label="Temperature" value={`${weather.temperature_c} C`} />
            <MiniMetric label="Humidity" value={`${weather.humidity_percent}%`} />
            <MiniMetric label="Rain chance" value={`${weather.rain_probability_percent}%`} />
            <MiniMetric label="Disease weather risk" value={weather.risk_level} />
          </div>
          <p className="muted">{weather.advisory}</p>
        </>
      ) : (
        <p className="muted">Allow location access to show weather risk and include it in new scan advice.</p>
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
        latitude: location.coordinates?.latitude,
        longitude: location.coordinates?.longitude,
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

function MyCrop({ crops, onCreated, onOpenTimeline }) {
  const [form, setForm] = useState(() => freshCropForm());
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const update = (key, value) => {
    setForm((current) => ({ ...current, [key]: value }));
  };

  const submit = async (event) => {
    event.preventDefault();
    setError("");
    setLoading(true);
    try {
      const payload = await createCrop(form);
      setForm(freshCropForm());
      onCreated(payload.crop);
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
              <h3>Crop profile</h3>
              <p>Required details build the lifecycle record.</p>
            </div>
          </div>

          <label className="field-label">
            Crop name
            <input value={form.crop_name} onChange={(event) => update("crop_name", event.target.value)} placeholder="Tomato" />
          </label>
          <label className="field-label">
            Field or plant name
            <input value={form.field_name} onChange={(event) => update("field_name", event.target.value)} placeholder="North Field" />
          </label>
          <label className="field-label">
            Planting date
            <input type="date" value={form.planting_date} onChange={(event) => update("planting_date", event.target.value)} />
          </label>
          <label className="field-label">
            Location optional
            <input value={form.location} onChange={(event) => update("location", event.target.value)} placeholder="Village, field block, greenhouse..." />
          </label>
          <label className="field-label">
            Notes optional
            <textarea value={form.notes} onChange={(event) => update("notes", event.target.value)} rows="4" placeholder="Variety, irrigation pattern, soil notes..." />
          </label>

          {error && <p className="form-error">{error}</p>}

          <button className="primary-button full-width" type="submit" disabled={loading}>
            {loading ? <Loader2 className="spin" size={18} /> : <Plus size={18} />}
            {loading ? "Creating..." : "Create Crop Profile"}
          </button>
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
                <button className="saved-crop-row" type="button" key={crop.id} onClick={() => onOpenTimeline(crop.id)}>
                  <span>
                    <strong>{crop.crop_name} - {crop.field_name}</strong>
                    <small>
                      Planted {formatDate(crop.planting_date)} - {crop.scan_count} scans - {crop.growth_stage}
                    </small>
                  </span>
                  <ChevronRight size={18} />
                </button>
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
  const scans = selectedCrop?.scans || [];
  const chartData = scans.map((scan) => ({
    name: `Day ${scan.day_number}`,
    scans: 1,
    health: scan.health_score,
  }));

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
          <div className="metric-grid">
            <MetricCard title="Days since planting" value={selectedCrop.days_since_planting} icon={CalendarDays} tone="green" />
            <MetricCard title="Estimated growth stage" value={selectedCrop.growth_stage} icon={Leaf} tone="emerald" />
            <MetricCard title="Latest health" value={selectedCrop.latest_health_status} icon={ShieldCheck} tone="amber" />
            <MetricCard title="Health trend" value={selectedCrop.health_trend} icon={LineChartIcon} tone="red" />
          </div>

          <article className="card crop-summary-card">
            <div>
              <p className="eyebrow">Profile details</p>
              <h3>{selectedCrop.crop_name}</h3>
              <p className="muted">
                {selectedCrop.field_name} - planted {formatDate(selectedCrop.planting_date)}
                {selectedCrop.location ? ` - ${selectedCrop.location}` : ""}
              </p>
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
              location={location}
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
