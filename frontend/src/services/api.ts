import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "",
  timeout: 60000,
  headers: {
    "Content-Type": "application/json",
  },
});

export interface Asset {
  id: number;
  name: string;
  asset_type: string;
  capacity_mw: number;
  location: string;
  is_active: boolean;
}

export interface HealthStatus {
  status: string;
  application: string;
}

export async function getHealth(): Promise<HealthStatus> {
  const response = await api.get<HealthStatus>("/health");
  return response.data;
}

export async function getAssets(): Promise<Asset[]> {
  const response = await api.get<Asset[]>("/assets/");
  return response.data;
}

export default api;

export interface Measurement {
  id: number;
  asset_id: number;
  timestamp: string;
  generation_mw: number;
  demand_mw: number | null;
  solar_irradiance: number | null;
  temperature_c: number | null;
  wind_speed_ms: number | null;
  cloud_cover_pct: number | null;
}

export async function getMeasurements(
  assetId?: number,
  limit = 100,
): Promise<Measurement[]> {
  const response = await api.get<Measurement[]>("/measurements/", {
    params: {
      ...(assetId !== undefined ? { asset_id: assetId } : {}),
      limit,
    },
  });

  return response.data;
}

export interface WeatherLocation {
  latitude: number;
  longitude: number;
  timezone: string;
}

export interface CurrentWeather {
  time: string;
  interval: number;
  temperature_2m: number;
  relative_humidity_2m: number;
  precipitation: number;
  cloud_cover: number;
  wind_speed_10m: number;
  wind_direction_10m: number;
  wind_speed_100m: number;
  wind_direction_100m: number;
  shortwave_radiation: number | null;
  direct_radiation: number | null;
}

export interface HourlyWeather {
  timestamp_utc: string;
  temperature_c: number;
  relative_humidity_pct: number;
  precipitation_mm: number;
  cloud_cover_pct: number;
  wind_speed_kmh: number;
  wind_speed_ms: number;
  wind_direction_deg: number;
  wind_speed_100m_ms: number;
  wind_direction_100m_deg: number;
  solar_radiation_wm2: number;
  direct_radiation_wm2: number;
}

export interface WeatherForecast {
  message: string;
  saved_records: number;
  weather: {
    location: WeatherLocation;
    retrieved_at_utc: string;
    current: CurrentWeather;
    hourly_forecast: HourlyWeather[];
    forecast_horizon_hours: number;
    forecast_start_utc: string;
    forecast_end_utc: string;
    source: string;
    forecast_type: string;
    fallback_status?: string;
  };
}

export async function getWeatherForecast(): Promise<WeatherForecast> {
  const response = await api.get<WeatherForecast>("/weather/");
  return response.data;
}

export interface DemandForecastConstraints {
  latest_observation_utc: string;
  earliest_forecast_timestamp_utc: string;
  latest_valid_forecast_timestamp_utc?: string;
  valid_forecast_timestamps_utc?: string[];
  required_lag_hours: number;
  interval_minutes: number;
  model_version: string;
  data_source: string;
}

export async function getDemandForecastConstraints(): Promise<DemandForecastConstraints> {
  const response = await api.get<DemandForecastConstraints>("/forecast/demand/constraints");
  return response.data;
}

export interface BatteryConfiguration {
  capacity_mwh: number;
  max_charge_mw: number;
  max_discharge_mw: number;
  min_soc_pct: number;
  max_soc_pct: number;
  charge_efficiency: number;
  discharge_efficiency: number;
  configured_soc_pct: number;
  is_available: boolean;
  state_source: string;
  updated_at: string;
}

export async function getBatteryConfiguration(): Promise<BatteryConfiguration> {
  const response = await api.get<BatteryConfiguration>("/battery/configuration");
  return response.data;
}

export async function saveBatteryConfiguration(
  configuration: Omit<BatteryConfiguration, "state_source" | "updated_at">,
): Promise<BatteryConfiguration> {
  const response = await api.put<BatteryConfiguration>("/battery/configuration", configuration);
  return response.data;
}

export interface WorkflowRun {
  workflow_id: string;
  status: string;
  approval_status: string;
  plan_version: number;
  created_at?: string;
  updated_at?: string;
  workflow?: Record<string, unknown>;
  approval_history?: Array<Record<string, unknown>>;
}

export async function getWorkflowRuns(): Promise<WorkflowRun[]> {
  const response = await api.get<WorkflowRun[]>("/workflow/runs");
  return response.data;
}

export async function getAlerts(status?: "open" | "acknowledged"): Promise<AlertRecord[]> {
  const response = await api.get<AlertRecord[]>("/alerts/", { params: status ? { status } : {} });
  return response.data;
}

export interface AlertRecord {
  id: number;
  workflow_id: string | null;
  asset_id: number | null;
  severity: string;
  title: string;
  reason: string;
  status: string;
  created_at: string;
  acknowledged_at: string | null;
}

export async function acknowledgeAlert(alertId: number): Promise<AlertRecord> {
  const response = await api.post<AlertRecord>(`/alerts/${alertId}/acknowledge`);
  return response.data;
}

export async function createAsset(payload: Omit<Asset, "id" | "is_active"> & { is_active?: boolean }): Promise<Asset> {
  const response = await api.post<Asset>("/assets/", payload);
  return response.data;
}

export async function updateAsset(assetId: number, payload: Partial<Omit<Asset, "id">>): Promise<Asset> {
  const response = await api.patch<Asset>(`/assets/${assetId}`, payload);
  return response.data;
}

export interface BatteryStatus extends Omit<BatteryConfiguration, "updated_at"> {
  current_energy_mwh: number;
  minimum_energy_mwh: number;
  maximum_energy_mwh: number;
  available_charge_energy_mwh: number;
  available_discharge_energy_mwh: number;
}

export async function getBatteryStatus(): Promise<BatteryStatus> {
  const response = await api.get<BatteryStatus>("/battery/status");
  return response.data;
}

export interface EnergyBalanceRequest {
  solar_generation_mw: number[];
  wind_generation_mw: number[];
  demand_mw: number[];
  timestamps_utc?: string[];
  tolerance_mw: number;
}

export interface EnergyBalanceInterval {
  timestamp_utc: string | null;
  solar_generation_mw: number;
  wind_generation_mw: number;
  total_generation_mw: number;
  demand_mw: number;
  balance_mw: number;
  surplus_mw: number;
  deficit_mw: number;
  status: "balanced" | "surplus" | "deficit";
}

export async function calculateEnergyBalance(payload: EnergyBalanceRequest): Promise<{ tolerance_mw: number; intervals: EnergyBalanceInterval[]; data_kind: string }> {
  const response = await api.post("/grid/balance", payload);
  return response.data;
}

export interface WorkflowStatus extends WorkflowRun {
  human_approved: boolean;
  waiting_for_human: boolean;
  resumable: boolean;
  replan_status: string | null;
  replan_attempts: number;
  grid_optimization: Record<string, unknown>;
  review_result: Record<string, unknown>;
  agent_results: Record<string, unknown>;
  execution_trace: string[];
  errors: string[];
  anomalies: Array<Record<string, unknown>>;
  battery_status: Record<string, unknown>;
  generation_forecast_mw: number[];
  demand_forecast_mw: number[];
  generation_forecast_timestamps: string[];
  demand_forecast_timestamps: string[];
  forecast_provenance: Record<string, unknown>;
  performance_analysis: Record<string, unknown>;
  state?: Record<string, unknown>;
}

export async function startWorkflow(payload: {
  latitude?: number;
  longitude?: number;
  initial_soc_pct?: number;
  terminal_soc_pct?: number;
  timestep_hours?: number;
  battery_capacity_mwh?: number;
  max_charge_mw?: number;
  max_discharge_mw?: number;
  min_soc_pct?: number;
  max_soc_pct?: number;
  charge_efficiency?: number;
  discharge_efficiency?: number;
  battery_is_available?: boolean;
  plan_version?: number;
  idempotency_key?: string;
} = {}): Promise<WorkflowStatus> {
  const storageKey = "renewable-energy-workflow-start-idempotency-key";
  let idempotencyKey = payload.idempotency_key ?? sessionStorage.getItem(storageKey);
  if (!idempotencyKey) {
    idempotencyKey = crypto.randomUUID();
    sessionStorage.setItem(storageKey, idempotencyKey);
  }
  try {
    const response = await api.post<WorkflowStatus>("/workflow/start", {
      ...payload,
      idempotency_key: idempotencyKey,
    }, { timeout: 60000 });
    sessionStorage.removeItem(storageKey);
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error) && error.response) sessionStorage.removeItem(storageKey);
    throw error;
  }
}

export async function getWorkflowStatus(workflowId: string): Promise<WorkflowStatus> {
  const response = await api.get<WorkflowStatus>(`/workflow/${workflowId}`);
  return response.data;
}

export async function submitWorkflowDecision(
  workflowId: string,
  payload: { decision: "approve" | "reject"; feedback?: string; plan_version: number },
): Promise<WorkflowStatus> {
  const response = await api.post<WorkflowStatus>(`/workflow/${workflowId}/approval`, payload);
  return response.data;
}

export async function listReportRuns(): Promise<WorkflowRun[]> {
  const response = await api.get<WorkflowRun[]>("/reports/runs");
  return response.data;
}

export async function downloadWorkflowReport(workflowId: string, periodStart?: string, periodEnd?: string): Promise<Blob> {
  const response = await api.get(`/reports/${workflowId}.pdf`, {
    responseType: "blob",
    params: {
      ...(periodStart ? { period_start: periodStart } : {}),
      ...(periodEnd ? { period_end: periodEnd } : {}),
    },
  });
  return response.data as Blob;
}