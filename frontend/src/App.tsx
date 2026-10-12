import { useCallback, useEffect, useState } from "react";
import axios from "axios";
import WeatherIntelligence from "./components/WeatherIntelligence";
import {
  AIOperationsPage,
  AlertCenterPage,
  BatteryStoragePage,
  EnergyOptimizationPage,
  PerformanceAnomaliesPage,
  ReportsPage,
} from "./components/OperationalPages";
import { ErrorBanner, MetricCard } from "./components/DashboardPrimitives";
import api from "./services/api";
import {
  CartesianGrid,
  Bar,
  BarChart,
  Cell,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  Activity,
  AlertTriangle,
  BatteryCharging,
  Bot,
  CheckCircle2,
  ClipboardList,
  CloudSun,
  FileText,
  GitBranch,
  Gauge,
  LayoutDashboard,
  Leaf,
  Radio,
  RefreshCw,
  Settings,
  ShieldCheck,
  Sun,
  Wind,
  XCircle,
  Zap,
} from "lucide-react";

import {
  getAssets,
  getDemandForecastConstraints,
  getHealth,
  getAlerts,
  getMeasurements,
  getWeatherForecast,
  getWorkflowRuns,
  calculateEnergyBalance,
  createAsset,
  updateAsset,
  type Asset,
  type EnergyBalanceInterval,
  type HealthStatus,
  type DemandForecastConstraints,
  type Measurement,
  type WorkflowRun,
} from "./services/api";

import "./App.css";

const navigation = [
  { title: "Overview", icon: LayoutDashboard, page: "Renewable Dashboard" },
  { title: "Assets", icon: Sun, page: "Renewable Assets" },
  { title: "Live Generation", icon: Radio, page: "Live Generation" },
  { title: "Weather", icon: CloudSun, page: "Weather Intelligence" },
  { title: "Generation Forecast", icon: Wind, page: "Generation Forecasting" },
  { title: "Demand Forecast", icon: Activity, page: "Demand Forecasting" },
  { title: "Energy Balance", icon: Zap, page: "Energy Balance" },
  { title: "Battery Storage", icon: BatteryCharging, page: "Battery Storage" },
  { title: "Optimization", icon: Gauge, page: "Energy Optimization" },
  { title: "Anomalies", icon: AlertTriangle, page: "Performance & Anomalies" },
  { title: "Alerts", icon: ShieldCheck, page: "Alert Center" },
  { title: "AI Operations", icon: Bot, page: "AI Operations Center" },
  { title: "Reports", icon: FileText, page: "Reports" },
];

function App() {
  const [activePage, setActivePage] = useState("Renewable Dashboard");

  const [assets, setAssets] = useState<Asset[]>([]);
  const [health, setHealth] = useState<HealthStatus | null>(null);

  const [measurements, setMeasurements] = useState<Measurement[]>([]);

  const [loading, setLoading] = useState(true);
  const [measurementsLoading, setMeasurementsLoading] = useState(false);

  const [error, setError] = useState<string | null>(null);
  const [measurementsError, setMeasurementsError] = useState<string | null>(null);

  const [lastUpdated, setLastUpdated] = useState<string | null>(null);

  const loadDashboard = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const [healthData, assetData] = await Promise.all([
        getHealth(),
        getAssets(),
      ]);

      setHealth(healthData);
      setAssets(assetData);
      try {
        setMeasurements(await getMeasurements(undefined, 100));
        setMeasurementsError(null);
      } catch {
        setMeasurementsError("Stored measurements are unavailable.");
      }
      setLastUpdated(new Date().toLocaleTimeString());
    } catch (err) {
      console.error("Dashboard API error:", err);

      setError(
        "Unable to retrieve dashboard data. Check that the backend is running on port 8001.",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  const loadMeasurements = useCallback(async () => {
    setMeasurementsLoading(true);
    setMeasurementsError(null);

    try {
      const data = await getMeasurements(undefined, 100);

      setMeasurements(data);
      setLastUpdated(new Date().toLocaleTimeString());
    } catch (err) {
      console.error("Measurement API error:", err);

      setMeasurementsError(
        "Unable to load measurements. Check the backend connection.",
      );
    } finally {
      setMeasurementsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadDashboard();
  }, [loadDashboard]);

  useEffect(() => {
    if (activePage === "Live Generation") {
      void loadMeasurements();
      const timer = window.setInterval(() => void loadMeasurements(), 60_000);
      return () => window.clearInterval(timer);
    }
    return undefined;
  }, [activePage, loadMeasurements]);

  const activeAssets = assets.filter((asset) => asset.is_active).length;

  const totalCapacity = assets
    .filter((asset) => asset.is_active && asset.asset_type !== "battery")
    .reduce((sum, asset) => sum + Number(asset.capacity_mw || 0), 0);

  function handlePageChange(page: string) {
    setActivePage(page);
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">
            <Leaf size={23} />
          </div>

          <div>
            <h1>Renewable AI</h1>
            <span>Energy Intelligence</span>
          </div>
        </div>

        <div className="sidebar-section-label">WORKSPACE</div>

        <nav className="navigation">
          {navigation.map((item) => {
            const Icon = item.icon;
            const selected = activePage === item.page;

            return (
              <button
                key={item.page}
                className={`nav-item ${selected ? "active" : ""}`}
                onClick={() => handlePageChange(item.page)}
                aria-current={selected ? "page" : undefined}
              >
                <Icon size={18} />
                <span>{item.title}</span>
              </button>
            );
          })}
        </nav>

        <div className="sidebar-footer">
          <div className="system-indicator">
            <span
              className={`status-dot ${
                health?.status === "running" ? "online" : ""
              }`}
            />

            <div>
              <strong>Backend</strong>
              <span>
                {health?.status === "running" ? "Connected" : "Disconnected"}
              </span>
            </div>
          </div>

          <div className="sidebar-version">Renewable Energy AI · v1.0.0</div>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div>
            <div className="breadcrumb">ENERGY MANAGEMENT / WORKSPACE</div>
            <h2>{activePage}</h2>
          </div>

          <div className="topbar-actions">
            <span className="environment-badge">
              <span className="status-dot online" />
              Development
            </span>

            <button
              className="refresh-button"
              onClick={() => {
                if (activePage === "Live Generation") {
                  void loadMeasurements();
                } else {
                  void loadDashboard();
                }
              }}
              disabled={loading || measurementsLoading}
              title="Refresh data from the backend"
            >
              <RefreshCw size={16} />
              {loading || measurementsLoading ? "Loading..." : "Refresh"}
            </button>
          </div>
        </header>

        {activePage === "Renewable Dashboard" && (
          <DashboardPage
            assets={assets}
            measurements={measurements}
            measurementsError={measurementsError}
            health={health}
            loading={loading}
            error={error}
            activeAssets={activeAssets}
            totalCapacity={totalCapacity}
            lastUpdated={lastUpdated}
            onRefresh={() => void loadDashboard()}
          />
        )}

        {activePage === "Renewable Assets" && (
          <AssetsPage
            assets={assets}
            loading={loading}
            error={error}
            onRefresh={() => void loadDashboard()}
          />
        )}

        {activePage === "Live Generation" && (
          <LiveGenerationPage
            measurements={measurements}
            loading={measurementsLoading}
            error={measurementsError}
            onRefresh={() => void loadMeasurements()}
          />
        )}

        {activePage === "Weather Intelligence" && <WeatherIntelligence />}

        {activePage === "Generation Forecasting" && <GenerationForecastingPage />}

        {activePage === "Demand Forecasting" && <DemandForecastingPage />}

        {activePage === "Energy Balance" && <EnergyBalancePage />}

        {activePage === "Battery Storage" && <BatteryStoragePage />}

        {activePage === "Energy Optimization" && <EnergyOptimizationPage />}

        {activePage === "Performance & Anomalies" && <PerformanceAnomaliesPage />}

        {activePage === "Alert Center" && <AlertCenterPage />}

        {activePage === "AI Operations Center" && <AIOperationsPage />}

        {activePage === "Reports" && <ReportsPage />}

        {!([
          "Renewable Dashboard",
          "Renewable Assets",
          "Live Generation",
          "Weather Intelligence",
          "Generation Forecasting",
          "Demand Forecasting",
          "Energy Balance",
          "Battery Storage",
          "Energy Optimization",
          "Performance & Anomalies",
          "Alert Center",
          "AI Operations Center",
          "Reports",
        ] as string[]).includes(activePage) && (
          <PageNotImplemented page={activePage} />
        )}
      </main>
    </div>
  );
}

/* -------------------------------------------------------
   Dashboard
------------------------------------------------------- */

interface DashboardPageProps {
  assets: Asset[];
  measurements: Measurement[];
  measurementsError: string | null;
  health: HealthStatus | null;
  loading: boolean;
  error: string | null;
  activeAssets: number;
  totalCapacity: number;
  lastUpdated: string | null;
  onRefresh: () => void;
}

function DashboardPage({
  assets,
  measurements,
  measurementsError,
  health,
  loading,
  error,
  activeAssets,
  totalCapacity,
  lastUpdated,
  onRefresh,
}: DashboardPageProps) {
  const [openAlertCount, setOpenAlertCount] = useState<number | null>(null);
  const [latestWorkflow, setLatestWorkflow] = useState<WorkflowRun | null>(null);

  const [forecastValues, setForecastValues] = useState<{
    solar: number;
    wind: number;
    timestamp: string;
  } | null>(null);
  const [forecastError, setForecastError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadForecasts() {
      try {
        const weatherResponse = await getWeatherForecast();
        const hours = weatherResponse.weather.hourly_forecast;
        const now = Date.now();

        const weather = hours.find(
          (item) => new Date(item.timestamp_utc).getTime() > now,
        );

        if (!weather) throw new Error("No future weather forecast available.");

        const inputs = {
          solar_irradiance_wm2: weather.solar_radiation_wm2,
          cloud_cover_pct: weather.cloud_cover_pct,
          temperature_c: weather.temperature_c,
          wind_speed_ms: weather.wind_speed_ms,
          wind_direction_deg: weather.wind_direction_deg,
          valid_timestamp_utc: weather.timestamp_utc,
        };

        const [solarResponse, windResponse] = await Promise.all([
          api.post("/generation-forecast/solar", inputs),
          api.post("/generation-forecast/wind", inputs),
        ]);

        if (!cancelled) {
          setForecastValues({
            solar: Number(solarResponse.data.predicted_generation_mw),
            wind: Number(windResponse.data.predicted_generation_mw),
            timestamp: weather.timestamp_utc,
          });
          setForecastError(null);
        }
      } catch {
        if (!cancelled) {
          setForecastValues(null);
          setForecastError(
            "Forecast unavailable. Check the weather and forecasting APIs.",
          );
        }
      }
    }

    void loadForecasts();

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    void getAlerts("open")
      .then((records) => setOpenAlertCount(records.length))
      .catch(() => setOpenAlertCount(null));
    void getWorkflowRuns()
      .then((runs) => setLatestWorkflow(runs[0] ?? null))
      .catch(() => setLatestWorkflow(null));
  }, []);

  const latestMeasurement = [...measurements].sort(
    (a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime(),
  )[0];
  const latestTimestamp = latestMeasurement
    ? new Date(latestMeasurement.timestamp).getTime()
    : null;
  const timestampMeasurements =
    latestTimestamp === null
      ? []
      : measurements.filter(
          (item) => new Date(item.timestamp).getTime() === latestTimestamp,
        );
  const activeSolarIds = new Set(
    assets
      .filter((asset) => asset.is_active && asset.asset_type.toLowerCase() === "solar")
      .map((asset) => asset.id),
  );
  const activeWindIds = new Set(
    assets
      .filter((asset) => asset.is_active && asset.asset_type.toLowerCase() === "wind")
      .map((asset) => asset.id),
  );
  const solarCandidates = timestampMeasurements.filter((item) =>
    activeSolarIds.has(item.asset_id),
  );
  const hasValidGeneration = (item: Measurement) =>
    typeof item.generation_mw === "number" && Number.isFinite(item.generation_mw);
  const solarReadings =
    activeSolarIds.size > 0 &&
    [...activeSolarIds].every((id) =>
      solarCandidates.some(
        (item) => item.asset_id === id && hasValidGeneration(item),
      ),
    )
      ? solarCandidates.filter(hasValidGeneration)
      : [];

  const activeRenewableIds = new Set([...activeSolarIds, ...activeWindIds]);
  const activeAssetNames = new Map(assets.map((asset) => [asset.id, asset.name]));
  const missingActiveSolar = [...activeSolarIds].filter(
    (id) =>
      !solarCandidates.some(
        (item) => item.asset_id === id && hasValidGeneration(item),
      ),
  );
  const missingRenewableReadings = [...activeRenewableIds].filter(
    (id) =>
      !timestampMeasurements.some(
        (item) => item.asset_id === id && hasValidGeneration(item),
      ),
  );
  const missingReadingDetail = (ids: number[]) =>
    ids.length
      ? `Missing aligned reading for ${ids
          .map((id) => activeAssetNames.get(id) ?? `asset ${id}`)
          .join(", ")}`
      : "No valid readings at the latest shared timestamp";

  const totalAtTimestamp =
    activeRenewableIds.size > 0 &&
    [...activeRenewableIds].every((id) =>
      timestampMeasurements.some(
        (item) => item.asset_id === id && hasValidGeneration(item),
      ),
    )
      ? timestampMeasurements
          .filter(
            (item) =>
              activeRenewableIds.has(item.asset_id) && hasValidGeneration(item),
          )
          .reduce((sum, item) => sum + Number(item.generation_mw), 0)
      : null;

  const demandValues = [
    ...new Set(
      timestampMeasurements.flatMap((item) =>
        typeof item.demand_mw === "number" && Number.isFinite(item.demand_mw)
          ? [item.demand_mw]
          : [],
      ),
    ),
  ];
  const latestDemand = demandValues.length === 1 ? demandValues[0] : undefined;
  const alignedBalance =
    totalAtTimestamp !== null && typeof latestDemand === "number"
      ? totalAtTimestamp - latestDemand
      : null;

  const workflowState = latestWorkflow?.workflow?.state as
    | Record<string, unknown>
    | undefined;
  const workflowOptimization = workflowState?.grid_optimization as
    | { schedule?: Array<Record<string, unknown>> }
    | undefined;
  const workflowSchedule = workflowOptimization?.schedule ?? [];
  const scheduledSoc = workflowSchedule.length
    ? Number(workflowSchedule[workflowSchedule.length - 1].battery_soc_pct)
    : null;

  const provenance = latestWorkflow?.workflow?.forecast_provenance as
    | Record<
        string,
        {
          evaluation_metrics?: Record<string, unknown>;
          model_data_source?: string;
        }
      >
    | undefined;
  const generationMetrics = provenance?.generation_forecasting
    ?.evaluation_metrics as
    | Record<string, { model?: { mae_mw?: number } }>
    | undefined;
  const demandMetrics = provenance?.demand_forecasting?.evaluation_metrics;
  const accuracyValues = [
    generationMetrics?.solar?.model?.mae_mw != null
      ? `Solar ${generationMetrics.solar.model.mae_mw.toFixed(3)}`
      : null,
    generationMetrics?.wind?.model?.mae_mw != null
      ? `Wind ${generationMetrics.wind.model.mae_mw.toFixed(3)}`
      : null,
    typeof demandMetrics?.model_mae_mw === "number"
      ? `Demand ${demandMetrics.model_mae_mw.toFixed(3)}`
      : null,
  ].filter(Boolean);

  const evaluationSources = [
    provenance?.generation_forecasting?.model_data_source,
    provenance?.demand_forecasting?.model_data_source,
  ].filter((source): source is string => Boolean(source));
  const usesSyntheticEvaluation = evaluationSources.some((source) =>
    source.toLowerCase().includes("synthetic"),
  );

  return (
    <section className="page-content">
      <div className="welcome-row">
        <div>
          <h3>Renewable Energy Overview</h3>
          <p>
            Monitor renewable assets and inspect energy-system data from your
            connected backend.
          </p>
        </div>

        <div className="updated-label">
          Last updated: {lastUpdated ?? "Not yet loaded"}
        </div>
      </div>

      {error && <ErrorBanner message={error} onRetry={onRefresh} />}

      <div className="metrics-grid">
        <MetricCard
          label="Registered Assets"
          value={loading ? "…" : String(assets.length)}
          detail="Retrieved from backend"
          icon={<Sun size={20} />}
        />

        <MetricCard
          label="Active Assets"
          value={loading ? "…" : String(activeAssets)}
          detail="Assets marked active"
          icon={<Activity size={20} />}
        />

        <MetricCard
          label="Installed Capacity"
          value={loading ? "…" : `${totalCapacity.toFixed(2)} MW`}
          detail="Active asset capacity"
          icon={<Zap size={20} />}
        />

        <MetricCard
          label="Backend Status"
          value={loading ? "Checking…" : health?.status ?? "Unavailable"}
          detail={health?.application ?? "Waiting for API response"}
          icon={<CheckCircle2 size={20} />}
        />

        <MetricCard
          label="Solar Generation"
          value={
            solarReadings.length
              ? solarReadings
                  .reduce((sum, item) => sum + Number(item.generation_mw), 0)
                  .toFixed(2) + " MW"
              : "Unavailable"
          }
          detail={
            solarReadings.length
              ? "Recorded measurements · " +
                new Date(latestMeasurement!.timestamp).toLocaleString()
              : missingReadingDetail(missingActiveSolar)
          }
          icon={<Sun size={20} />}
        />

        <MetricCard
          label="Wind Generation Forecast"
          value={
            forecastValues
              ? `${forecastValues.wind.toFixed(2)} MW`
              : "Unavailable"
          }
          detail={
            forecastValues
              ? `Experimental model forecast · ${new Date(
                  forecastValues.timestamp,
                ).toLocaleString()}`
              : forecastError ?? "Loading forecast"
          }
          icon={<Wind size={20} />}
        />

        <MetricCard
          label="Total Renewable Generation Forecast"
          value={
            forecastValues
              ? `${(forecastValues.solar + forecastValues.wind).toFixed(2)} MW`
              : "Unavailable"
          }
          detail={
            forecastValues
              ? `Solar + wind forecasts · ${new Date(
                  forecastValues.timestamp,
                ).toLocaleString()}`
              : forecastError ?? "Loading forecast"
          }
          icon={<Radio size={20} />}
        />

        <MetricCard
          label="Latest Recorded Demand"
          value={
            typeof latestDemand === "number"
              ? Number(latestDemand).toFixed(2) + " MW"
              : "Unavailable"
          }
          detail={
            typeof latestDemand === "number"
              ? "Measurement · " +
                new Date(latestMeasurement!.timestamp).toLocaleString()
              : measurementsError ?? "No numeric demand reading at the latest timestamp"
          }
          icon={<Activity size={20} />}
        />

        <MetricCard
          label={
            alignedBalance === null
              ? "Energy Balance"
              : alignedBalance > 0
                ? "Energy Surplus"
                : alignedBalance < 0
                  ? "Energy Deficit"
                  : "Balanced"
          }
          value={
            alignedBalance === null
              ? "Unavailable"
              : Math.abs(alignedBalance).toFixed(2) + " MW"
          }
          detail={
            alignedBalance === null
              ? totalAtTimestamp === null
                ? missingReadingDetail(missingRenewableReadings)
                : "No numeric demand value aligned with generation at this timestamp"
              : "Measured generation minus demand at the same timestamp"
          }
          icon={<Zap size={20} />}
        />

        <MetricCard
          label="Scheduled Battery SoC"
          value={
            scheduledSoc === null || !Number.isFinite(scheduledSoc)
              ? "Unavailable"
              : scheduledSoc.toFixed(1) + "%"
          }
          detail={
            scheduledSoc === null
              ? "No stored optimization schedule"
              : "Latest workflow schedule end state · recommendation"
          }
          icon={<BatteryCharging size={20} />}
        />

        <MetricCard
          label="Open Alerts"
          value={
            openAlertCount === null ? "Unavailable" : String(openAlertCount)
          }
          detail="Persisted backend alerts"
          icon={<AlertTriangle size={20} />}
        />

        <MetricCard
          label="Forecast MAE"
          value={
            accuracyValues.length
              ? accuracyValues.join(" · ") + " MW"
              : "Unavailable"
          }
          detail={
            accuracyValues.length
              ? usesSyntheticEvaluation
                ? "Synthetic-data held-out MAE; not validated real-world accuracy"
                : "Held-out model MAE from latest stored workflow"
              : "No stored held-out evaluation is available"
          }
          icon={<Gauge size={20} />}
        />
      </div>

      <AssetsTable assets={assets} loading={loading} />

      <div className="bottom-grid">
        <section className="panel">
          <div className="panel-heading">
            <div>
              <h3>System Connectivity</h3>
              <p>Current development environment</p>
            </div>
          </div>

          <div className="connection-list">
            <ConnectionRow
              label="FastAPI backend"
              detail="127.0.0.1:8001"
              connected={health?.status === "running"}
            />

            <ConnectionRow
              label="Asset API"
              detail="/assets/"
              connected={!loading && !error}
            />

            <ConnectionRow
              label="Dashboard"
              detail="React + TypeScript"
              connected
            />
          </div>
        </section>

        <section className="panel">
          <div className="panel-heading">
            <div>
              <h3>AI Operations</h3>
              <p>Agent workflow architecture</p>
            </div>

            <GitBranch size={19} />
          </div>

          <div className="agent-summary">
            <div className="agent-summary-icon">
              <Bot size={25} />
            </div>

            <div>
              <strong>7 specialist roles</strong>
              <p>
                Asset monitoring, weather intelligence, generation and demand
                forecasting, anomaly analysis, battery management, and grid
                coordination.
              </p>
            </div>
          </div>

          <div className="workflow-note">
            <ClipboardList size={17} />
            Workflow monitoring will be connected in the AI Operations page.
          </div>
        </section>
      </div>

      <div className="dashboard-disclaimer">
        <Settings size={15} />
        Asset metrics are retrieved from the backend. Operational forecasts and
        recommendations are displayed separately from recorded measurements.
      </div>
    </section>
  );
}

/* -------------------------------------------------------
   Renewable Assets
------------------------------------------------------- */

function AssetsPage({
  assets,
  loading,
  error,
  onRefresh,
}: {
  assets: Asset[];
  loading: boolean;
  error: string | null;
  onRefresh: () => void;
}) {
  const [draft, setDraft] = useState({
    name: "",
    asset_type: "solar",
    capacity_mw: "",
    location: "",
    is_active: true,
  });
  const [editingId, setEditingId] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const editAsset = (asset: Asset) => {
    setDraft({
      name: asset.name,
      asset_type: asset.asset_type,
      capacity_mw: String(asset.capacity_mw),
      location: asset.location,
      is_active: asset.is_active,
    });
    setEditingId(asset.id);
    setFormError(null);
  };

  const saveAsset = async () => {
    setSaving(true);
    setFormError(null);
    try {
      const payload = {
        name: draft.name,
        asset_type: draft.asset_type,
        capacity_mw: Number(draft.capacity_mw),
        location: draft.location,
        is_active: draft.is_active,
      };
      if (editingId === null) await createAsset(payload);
      else await updateAsset(editingId, payload);
      setDraft({
        name: "",
        asset_type: "solar",
        capacity_mw: "",
        location: "",
        is_active: true,
      });
      setEditingId(null);
      onRefresh();
    } catch (err) {
      const detail = axios.isAxiosError(err)
        ? err.response?.data?.detail
        : undefined;
      setFormError(
        typeof detail === "string"
          ? detail
          : err instanceof Error
            ? err.message
            : "Asset could not be saved.",
      );
    } finally {
      setSaving(false);
    }
  };

  return (
    <section className="page-content">
      <div className="welcome-row">
        <div>
          <h3>Renewable Asset Registry</h3>
          <p>Inspect assets registered in the backend database.</p>
        </div>

        <button
          className="refresh-button"
          onClick={onRefresh}
          disabled={loading}
        >
          <RefreshCw size={16} />
          Refresh assets
        </button>
      </div>

      {error && <ErrorBanner message={error} onRetry={onRefresh} />}

      <section className="panel forecast-input-panel">
        <div className="panel-heading">
          <div>
            <h3>{editingId === null ? "Register an asset" : "Edit asset"}</h3>
            <p>Asset information is saved in the backend registry.</p>
          </div>
        </div>
        <div className="forecast-input-grid">
          <label>
            Asset name
            <input
              value={draft.name}
              onChange={(event) =>
                setDraft({ ...draft, name: event.target.value })
              }
            />
          </label>
          <label>
            Type
            <select
              value={draft.asset_type}
              onChange={(event) =>
                setDraft({ ...draft, asset_type: event.target.value })
              }
            >
              <option value="solar">Solar</option>
              <option value="wind">Wind</option>
              <option value="battery">Battery</option>
            </select>
          </label>
          <label>
            Capacity (MW)
            <input
              type="number"
              min="0.01"
              step="0.1"
              value={draft.capacity_mw}
              onChange={(event) =>
                setDraft({ ...draft, capacity_mw: event.target.value })
              }
            />
          </label>
          <label>
            Location
            <input
              value={draft.location}
              onChange={(event) =>
                setDraft({ ...draft, location: event.target.value })
              }
            />
          </label>
          {editingId !== null && (
            <label className="ops-checkbox">
              <input
                type="checkbox"
                checked={draft.is_active}
                onChange={(event) =>
                  setDraft({ ...draft, is_active: event.target.checked })
                }
              />
              Asset active
            </label>
          )}
        </div>
        {formError && (
          <ErrorBanner message={formError} onRetry={() => void saveAsset()} />
        )}
        <div className="ops-actions">
          <button
            className="refresh-button"
            onClick={() => void saveAsset()}
            disabled={
              saving ||
              !draft.name.trim() ||
              !draft.location.trim() ||
              Number(draft.capacity_mw) <= 0
            }
          >
            {saving
              ? "Saving..."
              : editingId === null
                ? "Register asset"
                : "Save changes"}
          </button>
          {editingId !== null && (
            <button
              className="table-action"
              onClick={() => {
                setEditingId(null);
                setDraft({
                  name: "",
                  asset_type: "solar",
                  capacity_mw: "",
                  location: "",
                  is_active: true,
                });
              }}
            >
              Cancel edit
            </button>
          )}
        </div>
      </section>
      <AssetsTable assets={assets} loading={loading} onEdit={editAsset} />
    </section>
  );
}

function AssetsTable({
  assets,
  loading,
  onEdit,
}: {
  assets: Asset[];
  loading: boolean;
  onEdit?: (asset: Asset) => void;
}) {
  return (
    <section className="panel assets-panel">
      <div className="panel-heading">
        <div>
          <h3>Renewable Assets</h3>
          <p>Asset records retrieved from the backend API</p>
        </div>

        <span className="record-count">{assets.length} records</span>
      </div>

      {loading ? (
        <div className="empty-state">
          <RefreshCw size={22} className="loading-icon" />
          <p>Loading asset data…</p>
        </div>
      ) : assets.length === 0 ? (
        <div className="empty-state">
          <Sun size={25} />
          <p>No assets were returned by the API.</p>
        </div>
      ) : (
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Asset</th>
                <th>Type</th>
                <th>Capacity</th>
                <th>Location</th>
                <th>Status</th>
                {onEdit && <th>Actions</th>}
              </tr>
            </thead>

            <tbody>
              {assets.map((asset) => (
                <tr key={asset.id}>
                  <td>
                    <div className="asset-name">
                      <span className="asset-icon">
                        {asset.asset_type.toLowerCase() === "wind" ? (
                          <Wind size={17} />
                        ) : asset.asset_type.toLowerCase() === "battery" ? (
                          <BatteryCharging size={17} />
                        ) : (
                          <Sun size={17} />
                        )}
                      </span>

                      <div>
                        <strong>{asset.name}</strong>
                        <span>ID: {asset.id}</span>
                      </div>
                    </div>
                  </td>
                  <td>
                    <span className="type-badge">{asset.asset_type}</span>
                  </td>

                  <td>{Number(asset.capacity_mw).toFixed(2)} MW</td>
                  <td>{asset.location}</td>

                  <td>
                    <span
                      className={`asset-status ${
                        asset.is_active ? "active-status" : "inactive-status"
                      }`}
                    >
                      <span className="status-dot" />
                      {asset.is_active ? "Active" : "Inactive"}
                    </span>
                  </td>
                  {onEdit && (
                    <td>
                      <button
                        className="table-action"
                        onClick={() => onEdit(asset)}
                      >
                        Edit
                      </button>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

/* -------------------------------------------------------
   Live Generation
------------------------------------------------------- */

function LiveGenerationPage({
  measurements,
  loading,
  error,
  onRefresh,
}: {
  measurements: Measurement[];
  loading: boolean;
  error: string | null;
  onRefresh: () => void;
}) {
  const numericValue = (value: unknown): number | null =>
    typeof value === "number" && Number.isFinite(value) ? value : null;

  const validTimestampMeasurements = measurements.filter((item) =>
    Number.isFinite(new Date(item.timestamp).getTime()),
  );

  const latest = [...validTimestampMeasurements].sort(
    (a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime(),
  )[0];

  const latestGeneration = latest ? numericValue(latest.generation_mw) : null;
  const latestDemandValue = latest ? numericValue(latest.demand_mw) : null;
  const latestTimeMs = latest
    ? new Date(latest.timestamp).getTime()
    : Number.NaN;
  const readingAgeMs = Date.now() - latestTimeMs;

  const readingStatus = !Number.isFinite(latestTimeMs)
    ? "Invalid timestamp"
    : readingAgeMs < 0
      ? "Future timestamp"
      : readingAgeMs > 2 * 60 * 60 * 1000
        ? "Stale"
        : "Within 2-hour window";

  const readingAge = Number.isFinite(readingAgeMs)
    ? readingAgeMs < 0
      ? "Timestamp is in the future"
      : readingAgeMs < 60 * 60 * 1000
        ? `${Math.floor(readingAgeMs / 60000)} min old`
        : `${(readingAgeMs / 3600000).toFixed(1)} h old`
    : "Cannot determine reading age";

  const trend = [...validTimestampMeasurements]
    .filter((item) => numericValue(item.generation_mw) !== null)
    .sort(
      (a, b) =>
        new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime(),
    )
    .slice(-24)
    .map((item) => ({
      time: item.timestamp,
      generation: numericValue(item.generation_mw),
      demand: numericValue(item.demand_mw),
    }));

  return (
    <section className="page-content">
      <div className="welcome-row">
        <div>
          <h3>Recorded Generation Measurements</h3>
          <p>
            Generation, demand, and environmental readings retrieved from the
            Measurements API.
          </p>
        </div>
        <button className="refresh-button" onClick={onRefresh} disabled={loading}>
          <RefreshCw size={16} />
          {loading ? "Loading..." : "Refresh measurements"}
        </button>
      </div>

      {error && <ErrorBanner message={error} onRetry={onRefresh} />}

      {loading ? (
        <section className="panel empty-state">
          <RefreshCw size={22} className="loading-icon" />
          <p>Loading measurements...</p>
        </section>
      ) : measurements.length === 0 ? (
        <section className="panel empty-state">
          <Activity size={25} />
          <p>No measurement records were returned by the API.</p>
        </section>
      ) : (
        <>
          {latest && (
            <div className="metrics-grid">
              <MetricCard
                label="Latest Generation"
                value={
                  latestGeneration === null
                    ? "Unavailable"
                    : `${latestGeneration.toFixed(2)} MW`
                }
                detail={`Recorded ${new Date(
                  latest.timestamp,
                ).toLocaleString()} · asset ${latest.asset_id}`}
                icon={<Zap size={20} />}
              />
              <MetricCard
                label="Recorded Demand"
                value={
                  latestDemandValue === null
                    ? "Unavailable"
                    : `${latestDemandValue.toFixed(2)} MW`
                }
                detail="Latest stored measurement"
                icon={<Activity size={20} />}
              />
              <MetricCard
                label="Solar Irradiance"
                value={
                  numericValue(latest.solar_irradiance) === null
                    ? "Unavailable"
                    : `${numericValue(latest.solar_irradiance)!.toFixed(0)} W/m²`
                }
                detail="Recorded environmental input"
                icon={<Sun size={20} />}
              />
              <MetricCard
                label="Temperature"
                value={
                  numericValue(latest.temperature_c) === null
                    ? "Unavailable"
                    : `${numericValue(latest.temperature_c)!.toFixed(1)} °C`
                }
                detail={
                  latest.cloud_cover_pct == null
                    ? "Cloud cover unavailable"
                    : `Cloud cover: ${latest.cloud_cover_pct}%`
                }
                icon={<CloudSun size={20} />}
              />
              <MetricCard
                label="Reading Freshness"
                value={readingStatus}
                detail={`${readingAge} · stale after two expected hourly intervals`}
                icon={<Radio size={20} />}
              />
            </div>
          )}

          <section className="panel weather-forecast-panel">
            <div className="panel-heading">
              <div>
                <h3>Recorded generation and demand</h3>
                <p>Measurement API records · recorded values only.</p>
              </div>
              <span className="record-count">{trend.length} records</span>
            </div>

            {trend.length === 0 ? (
              <div className="empty-state">
                <Activity size={22} />
                <p>No valid generation readings are available to plot.</p>
              </div>
            ) : (
              <>
                {trend.length === 1 && (
                  <div className="empty-state">
                    <Activity size={22} />
                    <p>
                      One reading is available. More readings are needed to
                      establish a trend.
                    </p>
                  </div>
                )}

                <div
                  className="forecast-chart"
                  style={{ width: "100%", minWidth: 0, height: 300 }}
                >
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart
                      data={trend}
                      margin={{ top: 12, right: 24, left: 12, bottom: 12 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis
                        dataKey="time"
                        interval="preserveStartEnd"
                        tickFormatter={(value) =>
                          new Date(String(value)).toLocaleTimeString()
                        }
                      />
                      <YAxis
                        unit=" MW"
                        domain={["auto", "auto"]}
                        width={75}
                        tickFormatter={(value) => Number(value).toFixed(1)}
                      />
                      <Tooltip
                        labelFormatter={(value) =>
                          new Date(String(value)).toLocaleString()
                        }
                        formatter={(value, name) => [
                          typeof value === "number" && Number.isFinite(value)
                            ? `${value.toFixed(2)} MW`
                            : "Unavailable",
                          String(name ?? "Power"),
                        ]}
                      />
                      <Line
                        type="monotone"
                        dataKey="generation"
                        name="Recorded generation"
                        stroke="#2877c7"
                        strokeWidth={3}
                        dot={{ r: 6 }}
                        activeDot={{ r: 8 }}
                        connectNulls={false}
                      />
                      <Line
                        type="monotone"
                        dataKey="demand"
                        name="Recorded demand"
                        stroke="#e6a23c"
                        strokeWidth={3}
                        dot={{ r: 6 }}
                        activeDot={{ r: 8 }}
                        connectNulls={false}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </>
            )}
          </section>

          <section className="panel assets-panel">
            <div className="panel-heading">
              <div>
                <h3>Measurement History</h3>
                <p>Actual records returned by the Measurements API</p>
              </div>
              <span className="record-count">{measurements.length} records</span>
            </div>
            <div className="table-wrapper">
              <table>
                <thead>
                  <tr>
                    <th>Timestamp</th>
                    <th>Asset ID</th>
                    <th>Generation</th>
                    <th>Demand</th>
                    <th>Irradiance</th>
                    <th>Temperature</th>
                    <th>Wind Speed</th>
                    <th>Cloud Cover</th>
                  </tr>
                </thead>
                <tbody>
                  {measurements.map((item) => (
                    <tr key={item.id}>
                      <td>
                        {Number.isFinite(new Date(item.timestamp).getTime())
                          ? new Date(item.timestamp).toLocaleString()
                          : "Invalid timestamp"}
                      </td>
                      <td>{item.asset_id}</td>
                      <td>
                        {numericValue(item.generation_mw) === null
                          ? "Unavailable"
                          : `${numericValue(item.generation_mw)!.toFixed(2)} MW`}
                      </td>
                      <td>
                        {numericValue(item.demand_mw) === null
                          ? "Unavailable"
                          : `${numericValue(item.demand_mw)!.toFixed(2)} MW`}
                      </td>
                      <td>
                        {numericValue(item.solar_irradiance) === null
                          ? "—"
                          : `${numericValue(item.solar_irradiance)!.toFixed(0)} W/m²`}
                      </td>
                      <td>
                        {numericValue(item.temperature_c) === null
                          ? "—"
                          : `${numericValue(item.temperature_c)!.toFixed(1)} °C`}
                      </td>
                      <td>
                        {numericValue(item.wind_speed_ms) === null
                          ? "—"
                          : `${numericValue(item.wind_speed_ms)!.toFixed(1)} m/s`}
                      </td>
                      <td>
                        {numericValue(item.cloud_cover_pct) === null
                          ? "—"
                          : `${numericValue(item.cloud_cover_pct)!.toFixed(0)}%`}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <div className="dashboard-disclaimer">
            <Activity size={15} />
            These are recorded database measurements, not guaranteed live sensor
            readings. Timestamps indicate when each record was recorded.
          </div>
        </>
      )}
    </section>
  );
}

/* -------------------------------------------------------
   Demand Forecasting
------------------------------------------------------- */

interface DemandForecastResponse {
  demand_forecast_mw?: number[];
  demand_forecast_timestamps?: string[];
  agent_results?: {
    demand_forecasting?: {
      status?: string;
      forecasts?: Array<{
        timestamp_utc?: string;
        demand_forecast_mw?: number;
        demand_lag_24_mw?: number;
        lag_fallback_used?: boolean;
        lag_source?: string;
      }>;
      model_data_source?: string;
      forecast_scope?: string;
      forecast_method?: string;
      model_version?: string;
      evaluation_metrics?: {
        model_mae_mw?: number;
        model_rmse_mw?: number;
        same_hour_previous_day_mae_mw?: number;
        same_hour_previous_day_rmse_mw?: number;
        holdout_records?: number;
        holdout_start_utc?: string;
        holdout_end_utc?: string;
        evaluation_data_source?: string;
        evaluation_scope?: string;
      };
      message?: string;
      warning?: string;
    };
  };
  execution_trace?: string[];
  errors?: string[];
}

function DemandForecastingPage() {
  const [temperature, setTemperature] = useState(25);
  const [forecastTimestamp, setForecastTimestamp] = useState(() => {
    const nextUtcHour = new Date();
    nextUtcHour.setUTCHours(nextUtcHour.getUTCHours() + 1, 0, 0, 0);
    const local = (value: number) => String(value).padStart(2, "0");
    return `${nextUtcHour.getFullYear()}-${local(nextUtcHour.getMonth() + 1)}-${local(nextUtcHour.getDate())}T${local(nextUtcHour.getHours())}:${local(nextUtcHour.getMinutes())}`;
  });
  const [result, setResult] = useState<DemandForecastResponse | null>(null);
  const [constraints, setConstraints] = useState<DemandForecastConstraints | null>(
    null,
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void getDemandForecastConstraints()
      .then((data) => {
        setConstraints(data);
        const validTimestamps = data.valid_forecast_timestamps_utc ?? [];
        const selected = new Date(forecastTimestamp);
        const selectedIsValid = validTimestamps.some(
          (value) => new Date(value).getTime() === selected.getTime(),
        );
        if (validTimestamps.length > 0 && !selectedIsValid) {
          const earliest = new Date(validTimestamps[0]);
          const pad = (value: number) => String(value).padStart(2, "0");
          const localValue = `${earliest.getFullYear()}-${pad(earliest.getMonth() + 1)}-${pad(earliest.getDate())}T${pad(earliest.getHours())}:${pad(earliest.getMinutes())}`;
          setForecastTimestamp(localValue);
        }
      })
      .catch((err: unknown) => {
        if (axios.isAxiosError(err) && err.response?.status === 404) return;
        setError(
          axios.isAxiosError(err)
            ? String(err.response?.data?.detail ?? err.message)
            : err instanceof Error
              ? err.message
              : "Could not load demand history constraints.",
        );
      });
  }, []);

  const forecast = result?.agent_results?.demand_forecasting;
  const forecastRow = forecast?.forecasts?.[0];
  const prediction =
    result?.demand_forecast_mw?.[0] ?? forecastRow?.demand_forecast_mw;
  const hasObservedLag = forecastRow?.lag_source === "historical_observation";
  const chartData = [
    ...(hasObservedLag && typeof forecastRow?.demand_lag_24_mw === "number"
      ? [{ name: "Previous day", demand: forecastRow.demand_lag_24_mw }]
      : []),
    ...(typeof prediction === "number"
      ? [{ name: "Forecast", demand: prediction }]
      : []),
  ];

  const getErrorMessage = (err: unknown) => {
    if (axios.isAxiosError(err)) {
      const detail = err.response?.data?.detail;
      if (typeof detail === "string") return detail;
      if (Array.isArray(detail)) {
        return (
          detail
            .map((item) => {
              const location = Array.isArray(item.loc)
                ? item.loc.join(".")
                : "";
              return [location, item.msg].filter(Boolean).join(": ");
            })
            .filter(Boolean)
            .join("; ") || err.message
        );
      }
      return err.message;
    }
    return err instanceof Error ? err.message : "Demand forecast failed.";
  };

  const runForecast = async () => {
    const selectedTimestamp = new Date(forecastTimestamp);
    if (Number.isNaN(selectedTimestamp.getTime())) {
      setError("Enter a valid forecast timestamp.");
      return;
    }
    if (
      constraints &&
      selectedTimestamp < new Date(constraints.earliest_forecast_timestamp_utc)
    ) {
      setError(
        "Choose a forecast time with an exact observed demand value 24 hours earlier.",
      );
      return;
    }
    const validTimestamps = constraints?.valid_forecast_timestamps_utc;
    if (
      validTimestamps?.length &&
      !validTimestamps.some(
        (value) => new Date(value).getTime() === selectedTimestamp.getTime(),
      )
    ) {
      setError(
        "Choose one of the available forecast times with an exact observed demand value 24 hours earlier.",
      );
      return;
    }
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const response = await api.post<DemandForecastResponse>(
        "/forecast/demand",
        {
          forecast_timestamp: new Date(forecastTimestamp).toISOString(),
          temperature_c: temperature,
        },
      );
      setResult(response.data);
      if (
        response.data.agent_results?.demand_forecasting?.status !== "success"
      ) {
        setError(
          response.data.agent_results?.demand_forecasting?.message ??
            response.data.errors?.join("; ") ??
            "Demand forecast could not be generated.",
        );
      }
    } catch (err) {
      console.error("Demand forecast API error:", err);
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="page-content forecast-page">
      <div className="welcome-row">
        <div>
          <h3>Demand Forecasting</h3>
          <p>Estimate electricity demand for a selected forecast time.</p>
        </div>
        <button
          className="refresh-button"
          onClick={() => void runForecast()}
          disabled={loading}
        >
          <Activity size={16} className={loading ? "loading-icon" : ""} />
          {loading ? "Forecasting..." : "Run demand forecast"}
        </button>
      </div>

      <section className="panel forecast-input-panel">
        <div className="panel-heading">
          <div>
            <h3>Forecast Inputs</h3>
            <p>
              Provide the forecast timestamp and temperature used by the trained
              demand model.
            </p>
          </div>
        </div>
        <div className="forecast-input-grid">
          <label>
            Forecast time
            <input
              type="datetime-local"
              value={forecastTimestamp}
              onChange={(event) => setForecastTimestamp(event.target.value)}
            />
          </label>
          <label>
            Temperature (°C)
            <input
              type="number"
              min="-50"
              max="70"
              step="0.1"
              value={temperature}
              onChange={(event) => setTemperature(Number(event.target.value))}
            />
          </label>
        </div>
        {constraints && (
          <p className="ops-note">
            Exact previous-day observations are required. Earliest valid
            forecast:{" "}
            {new Date(
              constraints.earliest_forecast_timestamp_utc,
            ).toLocaleString()}
            . Source: {constraints.data_source}; model{" "}
            {constraints.model_version}.
          </p>
        )}
      </section>

      {error && (
        <ErrorBanner message={error} onRetry={() => void runForecast()} />
      )}

      <div className="metrics-grid">
        <MetricCard
          label="Predicted Demand"
          value={
            typeof prediction === "number" ? `${prediction.toFixed(4)} MW` : "—"
          }
          detail={
            forecastRow?.timestamp_utc
              ? new Date(forecastRow.timestamp_utc).toLocaleString()
              : "Run a forecast to calculate"
          }
          icon={<Activity size={20} />}
        />
        <MetricCard
          label="Previous-Day Demand"
          value={
            hasObservedLag && typeof forecastRow?.demand_lag_24_mw === "number"
              ? `${forecastRow.demand_lag_24_mw.toFixed(4)} MW`
              : "Unavailable"
          }
          detail={
            hasObservedLag
              ? "Exact historical observation 24 hours earlier"
              : forecastRow?.lag_fallback_used
                ? "No exact observation; model used a labelled fallback"
                : "Requires an exact historical observation 24 hours earlier"
          }
          icon={<RefreshCw size={20} />}
        />
        <MetricCard
          label="Model Status"
          value={
            forecast?.status === "success"
              ? "Successful"
              : loading
                ? "Running"
                : "Ready"
          }
          detail={
            forecast?.model_data_source ?? "Trained demand forecasting model"
          }
          icon={<CheckCircle2 size={20} />}
        />
        <MetricCard
          label="Forecast Scope"
          value={forecast?.forecast_scope ?? "—"}
          detail="Model output"
          icon={<Gauge size={20} />}
        />
      </div>

      <section className="panel weather-forecast-panel">
        <div className="panel-heading">
          <div>
            <h3>Demand Forecast Result</h3>
            <p>Predicted electricity demand for the selected time.</p>
          </div>
        </div>
        {chartData.length > 0 ? (
          <div className="forecast-chart">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={chartData}
                margin={{ top: 15, right: 20, left: 10, bottom: 10 }}
              >
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis unit=" MW" />
                <Tooltip
                  formatter={(value) => [
                    `${Number(value).toFixed(4)} MW`,
                    "Demand",
                  ]}
                />
                <Bar dataKey="demand" name="Demand" radius={[6, 6, 0, 0]}>
                  {chartData.map((item) => (
                    <Cell
                      key={item.name}
                      fill={item.name === "Previous day" ? "#8aa0b5" : "#2877c7"}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <div className="empty-state">
            <Activity size={25} />
            <p>Run a forecast to view the predicted electricity demand.</p>
          </div>
        )}
      </section>

      {(forecast?.warning ||
        (forecast?.evaluation_metrics &&
          Object.keys(forecast.evaluation_metrics).length > 0)) && (
        <section className="panel forecast-input-panel">
          <div className="panel-heading">
            <div>
              <h3>Model Information</h3>
              <p>
                {forecast.model_data_source ?? "Demand forecasting model"}
              </p>
            </div>
          </div>
          {forecast?.evaluation_metrics &&
            Object.keys(forecast.evaluation_metrics).length > 0 && (
              <div className="metrics-grid">
                {Object.entries(forecast.evaluation_metrics)
                  .filter(
                    (entry): entry is [string, number] =>
                      typeof entry[1] === "number",
                  )
                  .map(([name, value]) => (
                    <MetricCard
                      key={name}
                      label={name.replaceAll("_", " ")}
                      value={
                        name === "holdout_records"
                          ? String(value)
                          : value.toFixed(4) + " MW"
                      }
                      detail={
                        name === "holdout_records"
                          ? "Chronological holdout observations"
                          : "Model evaluation"
                      }
                      icon={<Gauge size={20} />}
                    />
                  ))}
              </div>
            )}
          {forecast.warning && <p>{forecast.warning}</p>}
        </section>
      )}
    </section>
  );
}

/* -------------------------------------------------------
   Energy Balance
------------------------------------------------------- */

function EnergyBalancePage() {
  const [inputs, setInputs] = useState({
    solar_mw: "",
    wind_mw: "",
    demand_mw: "",
    tolerance_mw: "0.1",
  });
  const [result, setResult] = useState<EnergyBalanceInterval | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const hasValidInputs =
    inputs.solar_mw.trim() !== "" &&
    inputs.wind_mw.trim() !== "" &&
    inputs.demand_mw.trim() !== "" &&
    [
      inputs.solar_mw,
      inputs.wind_mw,
      inputs.demand_mw,
      inputs.tolerance_mw,
    ].every(
      (value) => Number.isFinite(Number(value)) && Number(value) >= 0,
    );

  const updateInput = (key: keyof typeof inputs, value: string) => {
    setInputs((previous) => ({ ...previous, [key]: value }));
    setResult(null);
  };

  const calculate = async () => {
    if (!hasValidInputs) {
      setError(
        "Enter non-negative solar, wind, and demand values before calculating.",
      );
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const response = await calculateEnergyBalance({
        solar_generation_mw: [Number(inputs.solar_mw)],
        wind_generation_mw: [Number(inputs.wind_mw)],
        demand_mw: [Number(inputs.demand_mw)],
        tolerance_mw: Number(inputs.tolerance_mw),
      });
      setResult(response.intervals[0] ?? null);
    } catch (err) {
      const detail = axios.isAxiosError(err)
        ? err.response?.data?.detail
        : undefined;
      setError(
        typeof detail === "string"
          ? detail
          : err instanceof Error
            ? err.message
            : "Energy balance calculation failed.",
      );
    } finally {
      setLoading(false);
    }
  };

  const chartData = result
    ? [
        { name: "Solar", value: result.solar_generation_mw },
        { name: "Wind", value: result.wind_generation_mw },
        { name: "Demand", value: result.demand_mw },
      ]
    : [];

  return (
    <section className="page-content forecast-page">
      <div className="welcome-row">
        <div>
          <h3>Energy Balance Analysis</h3>
          <p>
            Compare renewable generation against demand for a user-entered
            scenario.
          </p>
        </div>
        <button
          className="refresh-button"
          onClick={() => void calculate()}
          disabled={loading || !hasValidInputs}
        >
          <Zap size={16} />
          {loading ? "Calculating..." : "Calculate balance"}
        </button>
      </div>

      {error && <ErrorBanner message={error} onRetry={() => void calculate()} />}
      <section className="panel forecast-input-panel">
        <div className="panel-heading">
          <div>
            <h3>Scenario Inputs</h3>
            <p>
              Enter values in MW. These are scenario inputs, not live readings. Set
              the balance tolerance in MW.
            </p>
          </div>
        </div>
        <div className="forecast-input-grid">
          <label>
            Solar generation (MW)
            <input
              type="number"
              min="0"
              step="0.1"
              value={inputs.solar_mw}
              onChange={(event) =>
                updateInput("solar_mw", event.target.value)
              }
            />
          </label>
          <label>
            Wind generation (MW)
            <input
              type="number"
              min="0"
              step="0.1"
              value={inputs.wind_mw}
              onChange={(event) =>
                updateInput("wind_mw", event.target.value)
              }
            />
          </label>
          <label>
            Energy demand (MW)
            <input
              type="number"
              min="0"
              step="0.1"
              value={inputs.demand_mw}
              onChange={(event) =>
                updateInput("demand_mw", event.target.value)
              }
            />
          </label>
          <label>
            Balance tolerance (MW)
            <input
              type="number"
              min="0"
              step="0.01"
              value={inputs.tolerance_mw}
              onChange={(event) =>
                updateInput("tolerance_mw", event.target.value)
              }
            />
          </label>
        </div>
      </section>

      {result && (
        <>
          <div className="metrics-grid">
            <MetricCard
              label="Total Renewable Generation"
              value={result.total_generation_mw.toFixed(2) + " MW"}
              detail="Backend calculated · scenario"
              icon={<Leaf size={20} />}
            />
            <MetricCard
              label="Demand"
              value={result.demand_mw.toFixed(2) + " MW"}
              detail="User-entered scenario"
              icon={<Activity size={20} />}
            />
            <MetricCard
              label={
                result.balance_mw >= 0 ? "Energy Surplus" : "Energy Deficit"
              }
              value={Math.abs(result.balance_mw).toFixed(2) + " MW"}
              detail={
                result.balance_mw >= 0
                  ? "Generation exceeds demand"
                  : "Demand exceeds generation"
              }
              icon={
                result.balance_mw >= 0 ? (
                  <CheckCircle2 size={20} />
                ) : (
                  <AlertTriangle size={20} />
                )}
            />
            <MetricCard
              label="Balance Status"
              value={result.status}
              detail={`Backend result · ±${Number(inputs.tolerance_mw).toFixed(2)} MW tolerance`}
              icon={<Zap size={20} />}
            />
          </div>
          <section className="panel weather-forecast-panel">
            <div className="panel-heading">
              <div>
                <h3>Generation and Demand Comparison</h3>
                <p>Values returned by the energy balance API.</p>
              </div>
            </div>
            <div className="forecast-chart">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={chartData}
                  margin={{ top: 15, right: 20, left: 10, bottom: 10 }}
                >
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" />
                  <YAxis unit=" MW" />
                  <Tooltip
                    formatter={(value) => [
                      Number(value).toFixed(2) + " MW",
                      "Power",
                    ]}
                  />
                  <Bar
                    dataKey="value"
                    name="Power"
                    fill="#2877c7"
                    radius={[6, 6, 0, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </section>
        </>
      )}
    </section>
  );
}

/* -------------------------------------------------------
   Generation Forecasting
------------------------------------------------------- */

type ForecastTarget = "solar" | "wind";

interface ForecastResponse {
  target: ForecastTarget;
  predicted_generation_mw: number;
  unit: string;
  model_source: string;
  data_source: string;
  validation_note: string;
  issued_at_utc?: string;
  valid_timestamp_utc?: string;
  model_version?: string;
  installed_capacity_mw?: number;
  clipped?: boolean;
  clipping_reason?: string | null;
  status?: string;
  evaluation?: {
    model?: { mae_mw?: number; rmse_mw?: number };
    persistence_baseline?: { mae_mw?: number; rmse_mw?: number };
  } | null;
  feature_order?: string[];
}

function GenerationForecastingPage() {
  const [weatherInputs, setWeatherInputs] = useState({
    solar_irradiance_wm2: 780,
    cloud_cover_pct: 15,
    temperature_c: 30,
    wind_speed_ms: 2.5,
    wind_direction_deg: 180,
  });
  const [solarResult, setSolarResult] = useState<ForecastResponse | null>(null);
  const [windResult, setWindResult] = useState<ForecastResponse | null>(null);
  const [weatherLoading, setWeatherLoading] = useState(false);
  const [validTimestamp, setValidTimestamp] = useState(() =>
    new Date().toISOString(),
  );
  const [inputSource, setInputSource] = useState("Manual weather scenario");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runForecast = async () => {
    setLoading(true);
    setError(null);
    try {
      const [solarResponse, windResponse] = await Promise.all([
        api.post<ForecastResponse>("/generation-forecast/solar", {
          ...weatherInputs,
          valid_timestamp_utc: validTimestamp,
        }),
        api.post<ForecastResponse>("/generation-forecast/wind", {
          ...weatherInputs,
          valid_timestamp_utc: validTimestamp,
        }),
      ]);
      setSolarResult(solarResponse.data);
      setWindResult(windResponse.data);
    } catch (err) {
      console.error("Generation forecast API error:", err);
      const detail = axios.isAxiosError(err)
        ? err.response?.data?.detail
        : undefined;
      setError(
        typeof detail === "string"
          ? detail
          : err instanceof Error
            ? err.message
            : "Unable to run generation forecasts.",
      );
    } finally {
      setLoading(false);
    }
  };

  const updateInput = (key: keyof typeof weatherInputs, value: string) => {
    const parsed = Number(value);
    setWeatherInputs((previous) => ({ ...previous, [key]: parsed }));
    setInputSource("Manual weather scenario");
  };

  const loadWeatherInputs = async () => {
    setWeatherLoading(true);
    setError(null);
    try {
      const response = await getWeatherForecast();
      const currentTime = Date.now();
      const forecast =
        response.weather.hourly_forecast.find(
          (item) => new Date(item.timestamp_utc).getTime() >= currentTime,
        ) ?? response.weather.hourly_forecast[0];
      if (!forecast)
        throw new Error("The weather API returned no hourly forecast records.");
      setWeatherInputs({
        solar_irradiance_wm2: forecast.solar_radiation_wm2,
        cloud_cover_pct: forecast.cloud_cover_pct,
        temperature_c: forecast.temperature_c,
        wind_speed_ms: forecast.wind_speed_ms,
        wind_direction_deg: forecast.wind_direction_deg,
      });
      setValidTimestamp(forecast.timestamp_utc);
      setInputSource(
        response.weather.source +
          " · " +
          new Date(forecast.timestamp_utc).toLocaleString(),
      );
    } catch (err) {
      const detail = axios.isAxiosError(err)
        ? err.response?.data?.detail
        : undefined;
      setError(
        typeof detail === "string"
          ? detail
          : err instanceof Error
            ? err.message
            : "Could not load weather forecast inputs.",
      );
    } finally {
      setWeatherLoading(false);
    }
  };

  const chartData = [
    ...(solarResult
      ? [{ source: "Solar", generation: solarResult.predicted_generation_mw }]
      : []),
    ...(windResult
      ? [{ source: "Wind", generation: windResult.predicted_generation_mw }]
      : []),
  ];

  return (
    <section className="page-content forecast-page">
      <div className="welcome-row">
        <div>
          <h3>Generation Forecasting</h3>
          <p>Run the trained solar and wind models using weather inputs.</p>
        </div>
        <button
          className="refresh-button"
          onClick={() => void runForecast()}
          disabled={loading}
        >
          <RefreshCw size={16} className={loading ? "loading-icon" : ""} />
          {loading ? "Predicting..." : "Run forecast"}
        </button>
      </div>

      <section className="panel forecast-input-panel">
        <div className="panel-heading">
          <div>
            <h3>Weather Inputs</h3>
            <p>
              Inputs from a weather forecast or an editable scenario. Source:{" "}
              {inputSource}.
            </p>
          </div>
          <button
            className="refresh-button"
            onClick={() => void loadWeatherInputs()}
            disabled={weatherLoading || loading}
          >
            <CloudSun size={16} />{" "}
            {weatherLoading ? "Loading weather..." : "Use next weather forecast"}
          </button>
        </div>
        <div className="forecast-input-grid">
          <label>
            Solar irradiance (W/m²)
            <input
              type="number"
              min="0"
              max="1500"
              value={weatherInputs.solar_irradiance_wm2}
              onChange={(event) =>
                updateInput("solar_irradiance_wm2", event.target.value)
              }
            />
          </label>
          <label>
            Cloud cover (%)
            <input
              type="number"
              min="0"
              max="100"
              value={weatherInputs.cloud_cover_pct}
              onChange={(event) =>
                updateInput("cloud_cover_pct", event.target.value)
              }
            />
          </label>
          <label>
            Temperature (°C)
            <input
              type="number"
              min="-50"
              max="70"
              value={weatherInputs.temperature_c}
              onChange={(event) =>
                updateInput("temperature_c", event.target.value)
              }
            />
          </label>
          <label>
            Wind speed (m/s)
            <input
              type="number"
              min="0"
              max="100"
              step="0.1"
              value={weatherInputs.wind_speed_ms}
              onChange={(event) =>
                updateInput("wind_speed_ms", event.target.value)
              }
            />
          </label>
          <label>
            Wind direction (°)
            <input
              type="number"
              min="0"
              max="360"
              value={weatherInputs.wind_direction_deg}
              onChange={(event) =>
                updateInput("wind_direction_deg", event.target.value)
              }
            />
          </label>
        </div>
      </section>

      {error && (
        <ErrorBanner message={error} onRetry={() => void runForecast()} />
      )}

      <div className="metrics-grid">
        <MetricCard
          label="Predicted Solar Generation"
          value={
            solarResult
              ? `${solarResult.predicted_generation_mw.toFixed(4)} MW`
              : "—"
          }
          detail={
            solarResult?.status === "no_active_capacity"
              ? "No active solar capacity is registered; output is constrained to zero"
              : solarResult
                ? "Experimental estimate · synthetic training data"
                : "Run forecast to calculate"
          }
          icon={<Sun size={20} />}
        />
        <MetricCard
          label="Predicted Wind Generation"
          value={
            windResult
              ? `${windResult.predicted_generation_mw.toFixed(4)} MW`
              : "—"
          }
          detail={
            windResult?.status === "no_active_capacity"
              ? "No active wind capacity is registered; output is constrained to zero"
              : windResult
                ? "Experimental estimate · synthetic training data"
                : "Run forecast to calculate"
          }
          icon={<Wind size={20} />}
        />
        <MetricCard
          label="Combined Model Output"
          value={
            solarResult && windResult
              ? `${(
                  solarResult.predicted_generation_mw +
                  windResult.predicted_generation_mw
                ).toFixed(4)} MW`
              : "—"
          }
          detail="Sum of model outputs; not a measured value"
          icon={<Zap size={20} />}
        />
        <MetricCard
          label="Model Status"
          value={solarResult && windResult ? "Successful" : "Ready"}
          detail="Solar and wind forecasting endpoints"
          icon={<CheckCircle2 size={20} />}
        />
      </div>

      <section className="panel weather-forecast-panel">
        <div className="panel-heading">
          <div>
            <h3>Solar vs Wind Prediction</h3>
            <p>Comparison of the latest model outputs for the selected inputs.</p>
          </div>
        </div>
        {chartData.length ? (
          <div className="forecast-chart">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={chartData}
                margin={{ top: 15, right: 20, left: 10, bottom: 10 }}
              >
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="source" />
                <YAxis unit=" MW" />
                <Tooltip
                  formatter={(value) => [
                    `${Number(value).toFixed(4)} MW`,
                    "Predicted generation",
                  ]}
                />
                <Bar
                  dataKey="generation"
                  name="Predicted generation"
                  fill="#2877c7"
                  radius={[6, 6, 0, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <div className="empty-state">
            <Wind size={25} />
            <p>Run a forecast to view the solar and wind comparison chart.</p>
          </div>
        )}
      </section>

      {(solarResult || windResult) && (
        <section className="panel forecast-input-panel">
          <div className="panel-heading">
            <div>
              <h3>Model Response Details</h3>
              <p>Provenance and validation notes returned by the backend.</p>
            </div>
          </div>
          <div className="forecast-response-list">
            {[solarResult, windResult]
              .filter((item): item is ForecastResponse => item !== null)
              .map((item) => (
                <div className="forecast-response-item" key={item.target}>
                  <strong>{item.target.toUpperCase()} model</strong>
                  <span>Artifact: {item.model_source}</span>
                  <span>Data source: {item.data_source}</span>
                  {item.valid_timestamp_utc && (
                    <span>
                      Valid time:{" "}
                      {new Date(item.valid_timestamp_utc).toLocaleString()}
                    </span>
                  )}
                  {item.model_version && (
                    <span>Model version: {item.model_version}</span>
                  )}
                  {typeof item.installed_capacity_mw === "number" && (
                    <span>
                      Registered active capacity:{" "}
                      {item.installed_capacity_mw.toFixed(2)} MW · status{" "}
                      {item.status}
                    </span>
                  )}
                  {item.clipped && (
                    <span>
                      Output constraint:{" "}
                      {item.clipping_reason ??
                        "Constrained by installed capacity or solar conditions."}
                    </span>
                  )}
                  {item.evaluation?.model && (
                    <span>
                      Held-out evaluation · MAE{" "}
                      {item.evaluation.model.mae_mw?.toFixed(4) ?? "—"} MW ·
                      RMSE {item.evaluation.model.rmse_mw?.toFixed(4) ?? "—"} MW
                    </span>
                  )}
                  {item.evaluation?.persistence_baseline && (
                    <span>
                      Persistence baseline · MAE{" "}
                      {item.evaluation.persistence_baseline.mae_mw?.toFixed(4) ??
                        "—"}{" "}
                      MW · RMSE{" "}
                      {item.evaluation.persistence_baseline.rmse_mw?.toFixed(4) ??
                        "—"}{" "}
                      MW
                    </span>
                  )}
                  <p>{item.validation_note}</p>
                </div>
              ))}
          </div>
        </section>
      )}

      <div className="dashboard-disclaimer">
        <AlertTriangle size={15} />
        These are experimental estimates from models trained on synthetic data.
        They are not validated real-world forecasts or live generation
        measurements. Demand forecasting is not implemented by these two
        models.
      </div>
    </section>
  );
}

/* -------------------------------------------------------
   Pages not yet implemented
------------------------------------------------------- */

function PageNotImplemented({ page }: { page: string }) {
  return (
    <section className="page-content">
      <section className="panel">
        <div className="panel-heading">
          <div>
            <h3>{page}</h3>
            <p>This page is awaiting its backend integration.</p>
          </div>

          <Settings size={20} />
        </div>

        <div className="empty-state">
          <ClipboardList size={27} />
          <p>
            This page has not been implemented yet. No simulated operational
            data is being presented as real data.
          </p>
        </div>
      </section>
    </section>
  );
}

/* -------------------------------------------------------
   Reusable components
------------------------------------------------------- */

function ConnectionRow({
  label,
  detail,
  connected,
}: {
  label: string;
  detail: string;
  connected: boolean;
}) {
  return (
    <div className="connection-row">
      <div>
        <strong>{label}</strong>
        <span>{detail}</span>
      </div>

      <span
        className={`connection-status ${
          connected ? "connected" : "disconnected"
        }`}
      >
        {connected ? <CheckCircle2 size={16} /> : <XCircle size={16} />}
        {connected ? "Connected" : "Unavailable"}
      </span>
    </div>
  );
}

export default App;