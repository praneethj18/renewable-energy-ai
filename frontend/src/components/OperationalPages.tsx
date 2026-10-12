import { useEffect, useMemo, useRef, useState } from "react";
import {
  Activity,
  AlertTriangle,
  BatteryCharging,
  CheckCircle2,
  Download,
  Gauge,
  RefreshCw,
  ShieldCheck,
  XCircle,
  Zap,
} from "lucide-react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import {
  acknowledgeAlert,
  downloadWorkflowReport,
  getAlerts,
  getBatteryConfiguration,
  getBatteryStatus,
  getWorkflowRuns,
  getWorkflowStatus,
  listReportRuns,
  saveBatteryConfiguration,
  startWorkflow,
  submitWorkflowDecision,
  type AlertRecord,
  type BatteryConfiguration,
  type BatteryStatus,
  type WorkflowRun,
  type WorkflowStatus,
} from "../services/api";
import api from "../services/api";
import { ErrorBanner, MetricCard } from "./DashboardPrimitives";

function apiError(error: unknown): string {
  if (typeof error === "object" && error !== null && "response" in error) {
    const response = (error as { response?: { data?: { detail?: unknown } } }).response;
    const detail = response?.data?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail.map((entry) => (typeof entry?.msg === "string" ? entry.msg : "Invalid input")).join("; ");
    }
  }
  return error instanceof Error ? error.message : "The request could not be completed.";
}

function localTimestamp(value?: string | null): string {
  if (!value) return "Not available";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

function readSchedule(result: WorkflowStatus | null): Array<Record<string, unknown>> {
  const optimization = result?.grid_optimization as { schedule?: unknown } | undefined;
  return Array.isArray(optimization?.schedule)
    ? (optimization.schedule as Array<Record<string, unknown>>)
    : [];
}

const EMPTY_FINDINGS: Array<Record<string, unknown>> = [];

export function BatteryStoragePage() {
  const [configuration, setConfiguration] = useState<BatteryConfiguration | null>(null);
  const [status, setStatus] = useState<BatteryStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  const refresh = async () => {
    setLoading(true);
    setError(null);
    try {
      const [config, batteryStatus] = await Promise.all([
        getBatteryConfiguration(),
        getBatteryStatus(),
      ]);
      setConfiguration(config);
      setStatus(batteryStatus);
    } catch (err) {
      setError(apiError(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void refresh();
  }, []);

  const update = (key: keyof BatteryConfiguration, value: string | boolean) => {
    if (!configuration) return;
    setConfiguration({ ...configuration, [key]: typeof value === "boolean" ? value : Number(value) });
    setSaved(false);
  };

  const save = async () => {
    if (!configuration) return;
    setSaving(true);
    setError(null);
    try {
      const next = await saveBatteryConfiguration({
        capacity_mwh: configuration.capacity_mwh,
        max_charge_mw: configuration.max_charge_mw,
        max_discharge_mw: configuration.max_discharge_mw,
        min_soc_pct: configuration.min_soc_pct,
        max_soc_pct: configuration.max_soc_pct,
        charge_efficiency: configuration.charge_efficiency,
        discharge_efficiency: configuration.discharge_efficiency,
        configured_soc_pct: configuration.configured_soc_pct,
        is_available: configuration.is_available,
      });
      setConfiguration(next);
      setSaved(true);
      await refresh();
    } catch (err) {
      setError(apiError(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <section className="page-content">
      <div className="welcome-row">
        <div>
          <h3>Battery Storage</h3>
          <p>Configured battery limits and calculated energy bounds.</p>
        </div>
        <button className="refresh-button" onClick={() => void refresh()} disabled={loading}>
          <RefreshCw size={16} /> Refresh
        </button>
      </div>
      {error && <ErrorBanner message={error} onRetry={() => void refresh()} />}
      {loading && (
        <div className="panel empty-state">
          <RefreshCw className="loading-icon" />
          <p>Loading battery configuration...</p>
        </div>
      )}
      {!loading && configuration && status && (
        <>
          <div className="metrics-grid">
            <MetricCard
              label="Configured SoC"
              value={`${status.configured_soc_pct.toFixed(1)}%`}
              detail="Configured value; battery telemetry is not connected"
              icon={<BatteryCharging size={20} />}
            />
            <MetricCard
              label="Stored Energy"
              value={`${status.current_energy_mwh.toFixed(2)} MWh`}
              detail="Capacity multiplied by configured SoC"
              icon={<Activity size={20} />}
            />
            <MetricCard
              label="Charge Available"
              value={`${status.available_charge_energy_mwh.toFixed(2)} MWh`}
              detail={`Maximum ${status.max_charge_mw.toFixed(2)} MW · ${Math.round(status.charge_efficiency * 100)}% efficiency`}
              icon={<Gauge size={20} />}
            />
            <MetricCard
              label="Discharge Available"
              value={`${status.available_discharge_energy_mwh.toFixed(2)} MWh`}
              detail={`Maximum ${status.max_discharge_mw.toFixed(2)} MW · ${Math.round(status.discharge_efficiency * 100)}% efficiency`}
              icon={<ShieldCheck size={20} />}
            />
          </div>
          <section className="panel">
            <div className="panel-heading">
              <div>
                <h3>Battery Configuration</h3>
                <p>Persisted backend configuration used by the optimizer.</p>
              </div>
              <span className={`asset-status ${configuration.is_available ? "active-status" : "inactive-status"}`}>
                {configuration.is_available ? "Available" : "Unavailable"}
              </span>
            </div>
            <div className="ops-form-grid">
              <NumberField label="Energy capacity (MWh)" value={configuration.capacity_mwh} min={0.01} step={0.1} onChange={(v) => update("capacity_mwh", v)} />
              <NumberField label="Maximum charge (MW)" value={configuration.max_charge_mw} min={0} step={0.1} onChange={(v) => update("max_charge_mw", v)} />
              <NumberField label="Maximum discharge (MW)" value={configuration.max_discharge_mw} min={0} step={0.1} onChange={(v) => update("max_discharge_mw", v)} />
              <NumberField label="Minimum SoC (%)" value={configuration.min_soc_pct} min={0} max={100} onChange={(v) => update("min_soc_pct", v)} />
              <NumberField label="Maximum SoC (%)" value={configuration.max_soc_pct} min={0.01} max={100} onChange={(v) => update("max_soc_pct", v)} />
              <NumberField label="Configured SoC (%)" value={configuration.configured_soc_pct} min={0} max={100} onChange={(v) => update("configured_soc_pct", v)} />
              <NumberField label="Charging efficiency (0–1)" value={configuration.charge_efficiency} min={0.01} max={1} step={0.01} onChange={(v) => update("charge_efficiency", v)} />
              <NumberField label="Discharging efficiency (0–1)" value={configuration.discharge_efficiency} min={0.01} max={1} step={0.01} onChange={(v) => update("discharge_efficiency", v)} />
              <label className="ops-checkbox">
                <input type="checkbox" checked={configuration.is_available} onChange={(event) => update("is_available", event.target.checked)} /> Battery available to optimizer
              </label>
            </div>
            <div className="ops-actions">
              <button className="refresh-button" onClick={() => void save()} disabled={saving}>
                {saving ? "Saving..." : "Save configuration"}
              </button>
              {saved && (
                <span className="ops-success">
                  <CheckCircle2 size={16} /> Saved
                </span>
              )}
            </div>
          </section>
        </>
      )}
    </section>
  );
}

export function EnergyOptimizationPage() {
  const runInProgress = useRef(false);
  const [configuration, setConfiguration] = useState<BatteryConfiguration | null>(null);
  const [result, setResult] = useState<WorkflowStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [runTimedOut, setRunTimedOut] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const schedule = useMemo(() => readSchedule(result), [result]);
  const optimization = result?.grid_optimization as {
    total_grid_import_mwh?: number;
    total_unmet_demand_mwh?: number;
    total_curtailed_generation_mwh?: number;
    total_efficiency_loss_mwh?: number;
    objective_value?: number;
    objective_description?: string;
    status?: string;
    feasible?: boolean;
  } | undefined;

  const energyValue = (value: number | undefined) =>
    typeof value === "number" ? value.toFixed(2) + " MWh" : "Unavailable";
  const runStatus =
    result?.waiting_for_human && result.status === "running"
      ? "awaiting human review"
      : result?.status ?? "Unavailable";

  useEffect(() => {
    void getBatteryConfiguration()
      .then(setConfiguration)
      .catch((err) => setError(apiError(err)));
  }, []);

  const run = async () => {
    if (runInProgress.current || runTimedOut) return;
    runInProgress.current = true;
    setLoading(true);
    setError(null);
    setResult(null);
    let workflowRequestStarted = false;
    let workflowRequestTimedOut = false;
    try {
      const config = configuration ?? (await getBatteryConfiguration());
      workflowRequestStarted = true;
      const runResult = await startWorkflow({
        latitude: 17.385,
        longitude: 78.4867,
        initial_soc_pct: config.configured_soc_pct,
        terminal_soc_pct: config.configured_soc_pct,
        timestep_hours: 1,
        battery_capacity_mwh: config.capacity_mwh,
        max_charge_mw: config.max_charge_mw,
        max_discharge_mw: config.max_discharge_mw,
        min_soc_pct: config.min_soc_pct,
        max_soc_pct: config.max_soc_pct,
        charge_efficiency: config.charge_efficiency,
        discharge_efficiency: config.discharge_efficiency,
        battery_is_available: config.is_available,
      });
      setResult(runResult);
      localStorage.setItem("renewable-energy-last-workflow", runResult.workflow_id);
    } catch (err) {
      const errorCode =
        typeof err === "object" && err !== null && "code" in err
          ? (err as { code?: unknown }).code
          : undefined;
      workflowRequestTimedOut =
        workflowRequestStarted && (errorCode === "ECONNABORTED" || errorCode === "ETIMEDOUT");
      setError(
        workflowRequestTimedOut
          ? "The workflow request timed out. The backend may still be finishing this run, so another run is disabled for this page session. Check stored runs in AI Operations Center before reloading."
          : apiError(err),
      );
      if (workflowRequestTimedOut) setRunTimedOut(true);
    } finally {
      if (!workflowRequestTimedOut) runInProgress.current = false;
      setLoading(false);
    }
  };

  return (
    <section className="page-content">
      <div className="welcome-row">
        <div>
          <h3>Energy Optimization</h3>
          <p>Run the backend forecasting, feasibility review, and battery schedule workflow.</p>
        </div>
        <button
          className="refresh-button"
          onClick={() => void run()}
          disabled={loading || runTimedOut || !configuration}
        >
          {runTimedOut ? "Run may still be processing" : loading ? "Calculating..." : "Calculate schedule"}
        </button>
      </div>
      {error && <ErrorBanner message={error} onRetry={() => void run()} />}
      {loading && (
        <div className="panel empty-state">
          <RefreshCw className="loading-icon" />
          <p>Fetching weather and calculating forecasts and constraints...</p>
        </div>
      )}
      {result && (
        <>
          <div className="metrics-grid">
            <MetricCard
              label="Run status"
              value={runStatus}
              detail={`Run ${result.workflow_id.slice(0, 8)} · plan v${result.plan_version}`}
              icon={<Activity size={20} />}
            />
            <MetricCard
              label="Forecast intervals"
              value={String(schedule.length)}
              detail="Aligned hourly backend forecasts"
              icon={<Gauge size={20} />}
            />
            <MetricCard
              label="Plan review"
              value={String((result.review_result as { status?: string }).status ?? "Pending").replaceAll("_", " ")}
              detail={result.waiting_for_human ? "Waiting for operator decision" : "Review result returned by backend"}
              icon={<ShieldCheck size={20} />}
            />
            <MetricCard
              label="Approval"
              value={result.approval_status}
              detail="A recommendation never controls equipment"
              icon={<CheckCircle2 size={20} />}
            />
          </div>
          {optimization && (
            <div className="metrics-grid">
              <MetricCard
                label="Grid imports"
                value={energyValue(optimization.total_grid_import_mwh)}
                detail="Energy over the workflow horizon"
                icon={<Activity size={20} />}
              />
              <MetricCard
                label="Unmet demand"
                value={energyValue(optimization.total_unmet_demand_mwh)}
                detail="Residual energy requirement"
                icon={<AlertTriangle size={20} />}
              />
              <MetricCard
                label="Curtailed generation"
                value={energyValue(optimization.total_curtailed_generation_mwh)}
                detail="Renewable energy not dispatched"
                icon={<Zap size={20} />}
              />
              <MetricCard
                label="Battery efficiency losses"
                value={energyValue(optimization.total_efficiency_loss_mwh)}
                detail="Energy lost across charge and discharge conversion"
                icon={<BatteryCharging size={20} />}
              />
              <MetricCard
                label="Optimizer objective score"
                value={typeof optimization.objective_value === "number" ? optimization.objective_value.toFixed(2) : "Unavailable"}
                detail={optimization.objective_description ?? "Weighted optimization objective; not a currency amount"}
                icon={<Gauge size={20} />}
              />
            </div>
          )}
          <section className="panel assets-panel">
            <div className="panel-heading">
              <div>
                <h3>Optimized Schedule</h3>
                <p>MW is power; battery state and conversion losses are shown in MWh.</p>
              </div>
              <span className="record-count">{schedule.length} intervals</span>
            </div>
            {schedule.length ? (
              <div className="table-wrapper">
                <table>
                  <thead>
                    <tr>
                      <th>Valid time</th>
                      <th>Generation</th>
                      <th>Demand</th>
                      <th>Before battery</th>
                      <th>Charge</th>
                      <th>Charge loss</th>
                      <th>Discharge</th>
                      <th>Discharge loss</th>
                      <th>Grid import</th>
                      <th>Unmet demand</th>
                      <th>Battery</th>
                      <th>SoC</th>
                    </tr>
                  </thead>
                  <tbody>
                    {schedule.map((row, index) => (
                      <tr key={`${String(row.timestamp_utc)}-${index}`}>
                        <td>{localTimestamp(String(row.timestamp_utc ?? ""))}</td>
                        <td>{Number(row.generation_mw).toFixed(2)} MW</td>
                        <td>{Number(row.demand_mw).toFixed(2)} MW</td>
                        <td>{Number(row.balance_before_battery_mw).toFixed(2)} MW</td>
                        <td>{Number(row.charge_mw).toFixed(2)} MW</td>
                        <td>{Number(row.charge_efficiency_loss_mwh ?? 0).toFixed(3)} MWh</td>
                        <td>{Number(row.discharge_mw).toFixed(2)} MW</td>
                        <td>{Number(row.discharge_efficiency_loss_mwh ?? 0).toFixed(3)} MWh</td>
                        <td>{Number(row.grid_import_mw).toFixed(2)} MW</td>
                        <td>{Number(row.unmet_demand_mw).toFixed(2)} MW</td>
                        <td>{Number(row.battery_energy_mwh).toFixed(2)} MWh</td>
                        <td>{Number(row.battery_soc_pct).toFixed(1)}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="empty-state">
                <AlertTriangle size={22} />
                <p>The workflow did not return a schedule. Review its errors and trace.</p>
              </div>
            )}
          </section>
          {schedule.length > 0 && (
            <section className="panel weather-forecast-panel">
              <div className="panel-heading">
                <div>
                  <h3>Battery SoC trajectory</h3>
                  <p>Backend optimizer output, in percent.</p>
                </div>
              </div>
              <div className="forecast-chart">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart
                    data={schedule.map((row) => ({
                      time: localTimestamp(String(row.timestamp_utc ?? "")),
                      soc: Number(row.battery_soc_pct),
                    }))}
                  >
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="time" interval="preserveStartEnd" />
                    <YAxis unit="%" />
                    <Tooltip />
                    <Line dataKey="soc" name="SoC" stroke="#087b5a" dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </section>
          )}
          <WorkflowSummary result={result} />
        </>
      )}
    </section>
  );
}

export function PerformanceAnomaliesPage() {
  const [runs, setRuns] = useState<WorkflowRun[]>([]);
  const [result, setResult] = useState<WorkflowStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = async () => {
    setLoading(true);
    setError(null);
    try {
      const stored = await getWorkflowRuns();
      setRuns(stored);
      const lastId = localStorage.getItem("renewable-energy-last-workflow") ?? stored[0]?.workflow_id;
      if (lastId) setResult(await getWorkflowStatus(lastId));
      else setResult(null);
    } catch (err) {
      setError(apiError(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void refresh();
  }, []);

  const anomalies = result?.anomalies ?? EMPTY_FINDINGS;
  const displayAnomalies = useMemo(() => {
    const unique = new Map<string, Record<string, unknown>>();
    for (const item of anomalies) {
      const key = JSON.stringify([
        item.type,
        item.timestep,
        item.timestamp_utc,
        item.generation_mw,
        item.demand_mw,
        item.deviation_mw,
        item.description,
      ]);
      if (!unique.has(key)) unique.set(key, item);
    }
    return [...unique.values()];
  }, [anomalies]);

  const comparison = result?.performance_analysis?.measurement_comparison as {
    status?: string;
    matched_timestamps?: number;
    screening_threshold_mw?: number | null;
    message?: string | null;
  } | undefined;

  const forecastTimestamps = result?.generation_forecast_timestamps ?? [];

  return (
    <section className="page-content">
      <div className="welcome-row">
        <div>
          <h3>Performance &amp; Anomalies</h3>
          <p>Findings from stored workflow analysis; no synthetic alert history is shown.</p>
        </div>
        <button className="refresh-button" onClick={() => void refresh()} disabled={loading}>
          <RefreshCw size={16} /> Refresh
        </button>
      </div>
      {error && <ErrorBanner message={error} onRetry={() => void refresh()} />}
      {loading ? (
        <div className="panel empty-state">
          <RefreshCw className="loading-icon" />
          <p>Loading stored analysis...</p>
        </div>
      ) : !runs.length ? (
        <section className="panel empty-state">
          <Activity size={24} />
          <p>No workflow analysis has been stored yet. Run a schedule from Energy Optimization to create one.</p>
        </section>
      ) : (
        <>
          <div className="metrics-grid">
            <MetricCard
              label="Latest analysis"
              value={String(result?.performance_analysis?.status ?? "Unavailable")}
              detail={result ? `Run ${result.workflow_id.slice(0, 8)} · ${localTimestamp(result.created_at)}` : "No accessible run"}
              icon={<Activity size={20} />}
            />
            <MetricCard
              label="Findings"
              value={String(displayAnomalies.length)}
              detail={
                displayAnomalies.length < anomalies.length
                  ? `${anomalies.length - displayAnomalies.length} exact duplicate payload(s) hidden`
                  : "Stored workflow findings"
              }
              icon={<AlertTriangle size={20} />}
            />
          </div>
          {comparison && (
            <section className="panel">
              <div className="panel-heading">
                <div>
                  <h3>Measured versus forecast generation</h3>
                  <p>Only exact timestamp matches are compared.</p>
                </div>
              </div>
              <p>
                Status: {comparison.status?.replaceAll("_", " ") ?? "Unavailable"} · {comparison.matched_timestamps ?? 0} aligned readings
              </p>
              <p>
                {comparison.message ??
                  (comparison.screening_threshold_mw != null
                    ? "Screening threshold: " + comparison.screening_threshold_mw.toFixed(2) + " MW, derived from held-out model error."
                    : "No screening threshold was available.")}
              </p>
            </section>
          )}
          {displayAnomalies.length ? (
            <section className="panel assets-panel">
              <div className="panel-heading">
                <div>
                  <h3>Investigation findings</h3>
                  <p>Forecast warnings, measured deviations, and asset-configuration findings are distinct evidence types.</p>
                </div>
                <span className="record-count">{displayAnomalies.length}</span>
              </div>
              <div className="table-wrapper">
                <table>
                  <thead>
                    <tr>
                      <th>Severity</th>
                      <th>Finding</th>
                      <th>Timestamp / forecast interval</th>
                      <th>Finding evidence</th>
                      <th>Investigation</th>
                    </tr>
                  </thead>
                  <tbody>
                    {displayAnomalies.map((item, index) => {
                      const isForecastImbalance = item.type === "generation_demand_imbalance";
                      const timestep = item.timestep;
                      const forecastTimestamp =
                        isForecastImbalance && typeof timestep === "number" && Number.isInteger(timestep) && timestep >= 0
                          ? forecastTimestamps[timestep]
                          : undefined;
                      const timestamp = isForecastImbalance ? forecastTimestamp : item.timestamp_utc;
                      const timestampText =
                        typeof timestamp === "string" && Number.isFinite(new Date(timestamp).getTime())
                          ? localTimestamp(timestamp)
                          : "Not available";
                      const demandMw = item.demand_mw;
                      const generationMw = item.generation_mw;
                      const shortfall =
                        typeof demandMw === "number" &&
                        Number.isFinite(demandMw) &&
                        typeof generationMw === "number" &&
                        Number.isFinite(generationMw)
                          ? demandMw - generationMw
                          : null;
                      const evidence = isForecastImbalance
                        ? shortfall === null
                          ? "Forecast shortfall (MW): Not available"
                          : `Forecast shortfall (MW): ${shortfall.toFixed(2)}`
                        : typeof item.deviation_mw === "number" && Number.isFinite(item.deviation_mw)
                          ? `Actual deviation: ${item.deviation_mw.toFixed(2)} MW`
                          : "Not available";
                      return (
                        <tr key={index}>
                          <td>{String(item.severity ?? "info")}</td>
                          <td>
                            <strong>{String(item.type ?? "Workflow finding").replaceAll("_", " ")}</strong>
                            <br />
                            {String(item.description ?? "")}
                          </td>
                          <td>{timestampText}</td>
                          <td>{evidence}</td>
                          <td>{String(item.investigation_status ?? "Review required")}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </section>
          ) : (
            <section className="panel empty-state">
              <CheckCircle2 size={23} />
              <p>No anomaly findings were returned. Check the aligned-reading status above before interpreting this as normal performance.</p>
            </section>
          )}
        </>
      )}
    </section>
  );
}

export function AlertCenterPage() {
  const [alerts, setAlerts] = useState<AlertRecord[]>([]);
  const [acknowledgingIds, setAcknowledgingIds] = useState<Set<number>>(new Set());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = async () => {
    setLoading(true);
    setError(null);
    try {
      setAlerts(await getAlerts());
    } catch (err) {
      setError(apiError(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void refresh();
  }, []);

  const acknowledge = async (id: number) => {
    if (acknowledgingIds.has(id)) return;
    setAcknowledgingIds((current) => new Set(current).add(id));
    setError(null);
    try {
      await acknowledgeAlert(id);
      await refresh();
    } catch (err) {
      setError(apiError(err));
    } finally {
      setAcknowledgingIds((current) => {
        const next = new Set(current);
        next.delete(id);
        return next;
      });
    }
  };

  const alertGroups = useMemo(() => {
    const groups = new Map<string, AlertRecord[]>();
    for (const alert of alerts) {
      const key = JSON.stringify([alert.severity, alert.title, alert.reason]);
      groups.set(key, [...(groups.get(key) ?? []), alert]);
    }
    return [...groups.entries()];
  }, [alerts]);

  return (
    <section className="page-content">
      <div className="welcome-row">
        <div>
          <h3>Alert Center</h3>
          <p>Workflow findings persisted by the backend, with acknowledgement status.</p>
        </div>
        <button className="refresh-button" onClick={() => void refresh()} disabled={loading}>
          <RefreshCw size={16} /> Refresh
        </button>
      </div>
      {error && <ErrorBanner message={error} onRetry={() => void refresh()} />}
      {loading ? (
        <div className="panel empty-state">
          <RefreshCw className="loading-icon" />
          <p>Loading alerts...</p>
        </div>
      ) : alerts.length ? (
        <section className="panel assets-panel">
          <div className="panel-heading">
            <div>
              <h3>Recorded alerts</h3>
              <p>
                {alerts.length} persisted records in {alertGroups.length} message groups. Every alert record is listed with its timestamp, status, and action.
              </p>
            </div>
            <span className="record-count">{alerts.length}</span>
          </div>
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Severity</th>
                  <th>Alert</th>
                  <th>Reason</th>
                  <th>ID</th>
                  <th>Workflow</th>
                  <th>Asset</th>
                  <th>Created</th>
                  <th>Status</th>
                  <th>Action</th>
                </tr>
              </thead>
              {alertGroups.map(([groupKey, records]) => {
                const first = records[0];
                return (
                  <tbody key={groupKey}>
                    <tr className="alert-group-summary">
                      <td colSpan={9}>
                        <strong>{first.title}</strong> · {first.severity} · {records.length} matching records · {first.reason}
                      </td>
                    </tr>
                    {records.map((alert) => (
                      <tr key={alert.id}>
                        <td>{alert.severity}</td>
                        <td>{alert.title}</td>
                        <td>{alert.reason}</td>
                        <td>{alert.id}</td>
                        <td>{alert.workflow_id ?? "Not available"}</td>
                        <td>{alert.asset_id ?? "System"}</td>
                        <td>{localTimestamp(alert.created_at)}</td>
                        <td>{alert.status}</td>
                        <td>
                          {alert.status === "open" ? (
                            <button className="table-action" onClick={() => void acknowledge(alert.id)} disabled={acknowledgingIds.has(alert.id)}>
                              {acknowledgingIds.has(alert.id) ? "Acknowledging..." : "Acknowledge"}
                            </button>
                          ) : (
                            localTimestamp(alert.acknowledged_at)
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                );
              })}
            </table>
          </div>
        </section>
      ) : (
        <section className="panel empty-state">
          <ShieldCheck size={24} />
          <p>No persisted alerts were returned.</p>
        </section>
      )}
    </section>
  );
}

export function AIOperationsPage() {
  const [runs, setRuns] = useState<WorkflowRun[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [result, setResult] = useState<WorkflowStatus | null>(null);
  const [feedback, setFeedback] = useState("");
  const [modify, setModify] = useState(false);
  const [initialSoc, setInitialSoc] = useState(45);
  const [terminalSoc, setTerminalSoc] = useState(45);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadRuns = async (preferred?: string) => {
    setLoading(true);
    setError(null);
    try {
      const stored = await getWorkflowRuns();
      setRuns(stored);
      const id = preferred ?? localStorage.getItem("renewable-energy-last-workflow") ?? stored[0]?.workflow_id ?? "";
      setSelectedId(id);
      if (id) {
        const detail = await getWorkflowStatus(id);
        setResult(detail);
        const initial = detail.state?.workflow_inputs as Record<string, unknown> | undefined;
        setInitialSoc(Number(initial?.initial_soc_pct ?? 45));
        setTerminalSoc(Number(initial?.terminal_soc_pct ?? 45));
      } else setResult(null);
    } catch (err) {
      setError(apiError(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadRuns();
  }, []);

  const selectRun = async (id: string) => {
    setSelectedId(id);
    setLoading(true);
    setError(null);
    try {
      setResult(await getWorkflowStatus(id));
    } catch (err) {
      setError(apiError(err));
    } finally {
      setLoading(false);
    }
  };

  const decide = async (decision: "approve" | "reject") => {
    if (!result) return;
    setLoading(true);
    setError(null);
    try {
      const updated = await submitWorkflowDecision(result.workflow_id, {
        decision,
        feedback,
        plan_version: result.plan_version,
      });
      setResult(updated);
      setFeedback("");
      await loadRuns(updated.workflow_id);
    } catch (err) {
      setError(apiError(err));
    } finally {
      setLoading(false);
    }
  };

  const recalculate = async () => {
    if (!result) return;
    setLoading(true);
    setError(null);
    try {
      const inputs = result.state?.workflow_inputs as Record<string, unknown> | undefined;
      const response = await api.post<WorkflowStatus>(`/workflow/${result.workflow_id}/recalculate`, {
        plan_version: result.plan_version,
        ...inputs,
        initial_soc_pct: initialSoc,
        terminal_soc_pct: terminalSoc,
      });
      const updated = response.data;
      localStorage.setItem("renewable-energy-last-workflow", updated.workflow_id);
      setResult(updated);
      await loadRuns(updated.workflow_id);
    } catch (err) {
      setError(apiError(err));
    } finally {
      setLoading(false);
    }
  };

  const agents = result?.agent_results ?? {};

  return (
    <section className="page-content">
      <div className="welcome-row">
        <div>
          <h3>AI Operations Center</h3>
          <p>Auditable agent outputs and workflow transitions. Explanations show evidence and results, not private chain-of-thought.</p>
        </div>
        <button className="refresh-button" onClick={() => void loadRuns()} disabled={loading}>
          <RefreshCw size={16} /> Refresh runs
        </button>
      </div>
      {error && <ErrorBanner message={error} onRetry={() => void loadRuns(selectedId)} />}
      <section className="panel ops-run-picker">
        <label>
          Stored workflow run
          <select value={selectedId} onChange={(event) => void selectRun(event.target.value)}>
            <option value="">Choose a run</option>
            {runs.map((run) => (
              <option key={run.workflow_id} value={run.workflow_id}>
                {run.workflow_id.slice(0, 8)} · {run.status} · plan v{run.plan_version}
              </option>
            ))}
          </select>
        </label>
        <span>{result ? `Plan v${result.plan_version} · ${result.approval_status}` : "No run selected"}</span>
      </section>
      {loading && (
        <div className="panel empty-state">
          <RefreshCw className="loading-icon" />
          <p>Loading workflow status...</p>
        </div>
      )}
      {result && !loading && (
        <>
          <div className="metrics-grid">
            <MetricCard
              label="Workflow state"
              value={result.waiting_for_human && result.status === "running" ? "Awaiting human review" : result.status.replaceAll("_", " ")}
              detail={
                result.waiting_for_human
                  ? "Waiting for operator review"
                  : result.resumable
                    ? "Current process checkpoint available"
                    : "Persisted snapshot; checkpoint not resumable after restart"
              }
              icon={<Activity size={20} />}
            />
            <MetricCard label="Plan version" value={`v${result.plan_version}`} detail={`Approval: ${result.approval_status}`} icon={<ShieldCheck size={20} />} />
            <MetricCard label="Execution steps" value={String(result.execution_trace.length)} detail="Recorded backend trace" icon={<CheckCircle2 size={20} />} />
            <MetricCard label="Errors" value={String(result.errors.length)} detail="Backend-reported errors" icon={<AlertTriangle size={20} />} />
          </div>
          <section className="panel assets-panel">
            <div className="panel-heading">
              <div>
                <h3>Agent results</h3>
                <p>Each result is returned by a workflow node or numerical service.</p>
              </div>
            </div>
            <div className="ops-agent-grid">
              {Object.entries(agents).map(([name, value]) => {
                const data = value as Record<string, unknown>;
                return (
                  <article className="ops-agent" key={name}>
                    <div>
                      <strong>{name.replaceAll("_", " ")}</strong>
                      <span className={`ops-status ops-${String(data.status ?? "unknown").replaceAll("_", "-")}`}>
                        {String(data.status ?? "completed")}
                      </span>
                    </div>
                    <p>{String(data.message ?? data.reviewer_note ?? data.warning ?? `${Object.keys(data).length} output fields recorded`)}</p>
                  </article>
                );
              })}
            </div>
          </section>
          <section className="panel assets-panel">
            <div className="panel-heading">
              <div>
                <h3>Execution trace</h3>
                <p>Ordered backend state transitions.</p>
              </div>
            </div>
            {result.execution_trace.length ? (
              <ol className="ops-trace">
                {result.execution_trace.map((entry, i) => (
                  <li key={`${entry}-${i}`}>{entry}</li>
                ))}
              </ol>
            ) : (
              <p>No trace entries were returned.</p>
            )}
            {result.errors.length > 0 && (
              <ul className="ops-errors">
                {result.errors.map((entry, i) => (
                  <li key={i}>{entry}</li>
                ))}
              </ul>
            )}
          </section>
          <section className="panel">
            <div className="panel-heading">
              <div>
                <h3>Operator review</h3>
                <p>Decisions are bound to the exact displayed plan version.</p>
              </div>
            </div>
            <pre className="ops-review">{JSON.stringify(result.review_result, null, 2)}</pre>
            {result.waiting_for_human && result.resumable ? (
              <div className="ops-decision">
                <label>
                  Rejection feedback
                  <textarea value={feedback} onChange={(event) => setFeedback(event.target.value)} placeholder="Required when rejecting the plan" />
                </label>
                <div className="ops-actions">
                  <button className="ops-approve" onClick={() => void decide("approve")} disabled={loading}>
                    <CheckCircle2 size={16} /> Approve plan v{result.plan_version}
                  </button>
                  <button className="ops-reject" onClick={() => void decide("reject")} disabled={loading || !feedback.trim()}>
                    <XCircle size={16} /> Reject with feedback
                  </button>
                  <button className="refresh-button" onClick={() => setModify((shown) => !shown)}>
                    Modify assumptions
                  </button>
                </div>
                {modify && (
                  <div className="ops-recalculate">
                    <NumberField label="Initial SoC (%)" value={initialSoc} min={10} max={90} onChange={(v) => setInitialSoc(Number(v))} />
                    <NumberField label="Terminal SoC (%)" value={terminalSoc} min={10} max={90} onChange={(v) => setTerminalSoc(Number(v))} />
                    <button className="refresh-button" onClick={() => void recalculate()} disabled={loading}>
                      Recalculate as a new plan version
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <p className="ops-note">This run is not awaiting a decision. The saved state remains available for review.</p>
            )}
          </section>
        </>
      )}
    </section>
  );
}

export function ReportsPage() {
  const [runs, setRuns] = useState<WorkflowRun[]>([]);
  const [selected, setSelected] = useState("");
  const [periodStart, setPeriodStart] = useState("");
  const [periodEnd, setPeriodEnd] = useState("");
  const [loading, setLoading] = useState(true);
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const filteredRuns = useMemo(
    () =>
      runs.filter((run) => {
        if (!run.created_at) return !periodStart && !periodEnd;
        const createdAt = new Date(run.created_at).getTime();
        const start = periodStart ? Date.parse(`${periodStart}T00:00:00Z`) : Number.NEGATIVE_INFINITY;
        const end = periodEnd ? Date.parse(`${periodEnd}T23:59:59.999Z`) : Number.POSITIVE_INFINITY;
        return createdAt >= start && createdAt <= end;
      }),
    [runs, periodStart, periodEnd],
  );

  useEffect(() => {
    setSelected((current) =>
      filteredRuns.some((run) => run.workflow_id === current)
        ? current
        : filteredRuns[0]?.workflow_id ?? "",
    );
  }, [filteredRuns]);

  const refresh = async () => {
    setLoading(true);
    setError(null);
    try {
      const stored = await listReportRuns();
      setRuns(stored);
      setSelected((current) => current || stored[0]?.workflow_id || "");
    } catch (err) {
      setError(apiError(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void refresh();
  }, []);

  const download = async () => {
    if (!selected) return;
    setDownloading(true);
    setError(null);
    try {
      const blob = await downloadWorkflowReport(selected, periodStart || undefined, periodEnd || undefined);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `renewable-energy-${selected}.pdf`;
      link.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(apiError(err));
    } finally {
      setDownloading(false);
    }
  };

  return (
    <section className="page-content">
      <div className="welcome-row">
        <div>
          <h3>Reports</h3>
          <p>Create a PDF from a selected stored workflow run and related records.</p>
        </div>
        <button className="refresh-button" onClick={() => void refresh()} disabled={loading}>
          <RefreshCw size={16} /> Refresh runs
        </button>
      </div>
      {error && <ErrorBanner message={error} onRetry={() => void refresh()} />}
      {loading ? (
        <div className="panel empty-state">
          <RefreshCw className="loading-icon" />
          <p>Loading stored runs...</p>
        </div>
      ) : runs.length ? (
        <section className="panel">
          <div className="ops-form-grid">
            <label className="ops-field">
              Period start (UTC)
              <input type="date" value={periodStart} onChange={(event) => setPeriodStart(event.target.value)} />
            </label>
            <label className="ops-field">
              Period end (UTC)
              <input type="date" value={periodEnd} onChange={(event) => setPeriodEnd(event.target.value)} />
            </label>
          </div>
          <div className="ops-run-picker">
            <label>
              Stored workflow run
              <select value={selected} onChange={(event) => setSelected(event.target.value)}>
                <option value="">Choose a run</option>
                {filteredRuns.map((run) => (
                  <option key={run.workflow_id} value={run.workflow_id}>
                    {run.workflow_id.slice(0, 8)} · {run.status} · {localTimestamp(run.created_at)}
                  </option>
                ))}
              </select>
            </label>
            <button className="refresh-button" onClick={() => void download()} disabled={!selected || downloading}>
              <Download size={16} /> {downloading ? "Preparing PDF..." : "Download PDF"}
            </button>
          </div>
          {filteredRuns.length === 0 && <p className="ops-note">No stored workflow runs fall within this reporting period.</p>}
          <div className="ops-report-contents">
            <h3>PDF report contents</h3>
            <p>
              The report is generated from the selected persisted workflow run and related database records. The selected UTC period is applied to timestamped records where supported.
            </p>
            <ul>
              <li>Executive summary, run status, plan version, reporting period and approval status</li>
              <li>Registered assets, capacities, and recorded measurements with source/quality where available</li>
              <li>Stored weather context and timestamped weather values</li>
              <li>Generation and demand forecasts, model provenance, and aligned-measurement accuracy evidence</li>
              <li>Energy balance, optimization schedule, grid imports/exports, unmet demand, and battery state of charge</li>
              <li>Anomaly findings, persisted alerts, and workflow execution trace</li>
              <li>Recorded operator decisions, recommendations, and sign-off fields</li>
            </ul>
            <p className="ops-note">
              Unavailable values remain marked as unavailable. Forecasts and optimization schedules are not presented as measured generation or executed grid dispatch.
            </p>
          </div>
        </section>
      ) : (
        <section className="panel empty-state">
          <Download size={24} />
          <p>No stored workflow runs are available to report.</p>
        </section>
      )}
    </section>
  );
}

function WorkflowSummary({ result }: { result: WorkflowStatus }) {
  const balance = result.grid_optimization as {
    total_grid_import_mwh?: number;
    total_unmet_demand_mwh?: number;
    objective?: string;
    message?: string;
    reviewer_validation?: unknown;
  };
  return (
    <section className="panel">
      <div className="panel-heading">
        <div>
          <h3>Recommendation review</h3>
          <p>{String(balance.message ?? "Backend optimization output")}</p>
        </div>
      </div>
      <div className="ops-review-grid">
        <span>
          Grid import: <strong>{Number(balance.total_grid_import_mwh ?? 0).toFixed(2)} MWh</strong>
        </span>
        <span>
          Unmet demand: <strong>{Number(balance.total_unmet_demand_mwh ?? 0).toFixed(2)} MWh</strong>
        </span>
        <span>
          Human review: <strong>{result.approval_status}</strong>
        </span>
        <span>
          Version: <strong>v{result.plan_version}</strong>
        </span>
      </div>
      {result.errors.length > 0 && (
        <ul className="ops-errors">
          {result.errors.map((entry, i) => (
            <li key={i}>{entry}</li>
          ))}
        </ul>
      )}
    </section>
  );
}

function NumberField({
  label,
  value,
  min,
  max,
  step = 0.1,
  onChange,
}: {
  label: string;
  value: number;
  min: number;
  max?: number;
  step?: number;
  onChange: (value: string) => void;
}) {
  return (
    <label className="ops-field">
      {label}
      <input type="number" value={value} min={min} max={max} step={step} onChange={(event) => onChange(event.target.value)} />
    </label>
  );
}