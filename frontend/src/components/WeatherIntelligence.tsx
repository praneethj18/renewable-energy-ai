import { useCallback, useEffect, useState } from "react";
import {
  CloudSun,
  Droplets,
  RefreshCw,
  Sun,
  Thermometer,
  Wind,
  CloudRain,
  MapPin,
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
  getWeatherForecast,
  type WeatherForecast,
} from "../services/api";

import "./WeatherIntelligence.css";

function formatForecastHour(timestamp: string): string {
  return new Date(timestamp).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatForecastDate(timestamp: string): string {
  return new Date(timestamp).toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function WeatherIntelligence() {
  const [data, setData] = useState<WeatherForecast | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadWeather = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const result = await getWeatherForecast();
      setData(result);
    } catch (err) {
      console.error("Weather API error:", err);

      setError(
        "Could not load weather data. Check that the backend is running on port 8001.",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadWeather();
  }, [loadWeather]);

  if (loading && !data) {
    return (
      <section className="page-content">
        <div className="weather-status">
          <RefreshCw className="weather-spin" size={24} />
          <p>Loading weather forecast...</p>
        </div>
      </section>
    );
  }

  if (error && !data) {
    return (
      <section className="page-content">
        <div className="weather-error">
          <CloudRain size={28} />
          <h3>Weather data unavailable</h3>
          <p>{error}</p>
          <button onClick={() => void loadWeather()}>
            Try again
          </button>
        </div>
      </section>
    );
  }

  const weather = data?.weather;

  if (!weather) {
    return (
      <section className="page-content">
        <p>No weather data is available.</p>
      </section>
    );
  }

  const current = weather.current;
  const forecast = weather.hourly_forecast;

  const chartData = forecast.map((item) => ({
    timestamp: item.timestamp_utc,
    time: formatForecastHour(item.timestamp_utc),
    temperature: item.temperature_c,
    solarRadiation: item.solar_radiation_wm2,
  }));

  return (
    <section className="page-content weather-page">
      {/* Page heading */}
      <div className="welcome-row">
        <div>
          <h3>Weather Intelligence</h3>
          <p>
            Weather conditions and forecasts for renewable energy planning.
          </p>
        </div>

        <button
          className="refresh-button"
          onClick={() => void loadWeather()}
          disabled={loading}
        >
          <RefreshCw
            size={16}
            className={loading ? "weather-spin" : ""}
          />
          {loading ? "Refreshing..." : "Refresh forecast"}
        </button>
      </div>

      {error && <p className="weather-inline-error">{error}</p>}

      {/* Current weather hero */}
      <section className="weather-hero">
        <div>
          <div className="weather-location">
            <MapPin size={16} />
            Renewable Energy Site
          </div>

          <div className="weather-temperature">
            {current.temperature_2m.toFixed(1)}
            <span>°C</span>
          </div>

          <p>Current temperature</p>

          <small>
            {weather.location.latitude.toFixed(4)}° N,{" "}
            {weather.location.longitude.toFixed(4)}° E
          </small>
        </div>

        <CloudSun size={76} strokeWidth={1.4} />

        <div className="weather-hero-details">
          <div>
            <span>Humidity</span>
            <strong>{current.relative_humidity_2m}%</strong>
          </div>

          <div>
            <span>Wind speed</span>
            <strong>{current.wind_speed_10m} m/s</strong>
          </div>

          <div>
            <span>Precipitation</span>
            <strong>{current.precipitation} mm</strong>
          </div>
        </div>
      </section>

      {/* Current condition cards */}
      <div className="weather-section-title">
        <h3>Current Conditions</h3>
        <p>Latest values returned by the weather API.</p>
      </div>

      <div className="metrics-grid">
        <WeatherCard
          label="Temperature"
          value={`${current.temperature_2m.toFixed(1)} °C`}
          icon={<Thermometer size={21} />}
        />

        <WeatherCard
          label="Humidity"
          value={`${current.relative_humidity_2m}%`}
          icon={<Droplets size={21} />}
        />

        <WeatherCard
          label="Wind Speed"
          value={`${current.wind_speed_10m} m/s`}
          icon={<Wind size={21} />}
        />

        <WeatherCard
          label="Cloud Cover"
          value={`${current.cloud_cover}%`}
          icon={<CloudSun size={21} />}
        />

        <WeatherCard
          label="Precipitation"
          value={`${current.precipitation} mm`}
          icon={<CloudRain size={21} />}
        />

        <WeatherCard
          label="Solar Radiation"
          value={
            current.shortwave_radiation == null
              ? "Unavailable"
              : `${current.shortwave_radiation} W/m²`
          }
          icon={<Sun size={21} />}
        />
      </div>

      {/* Temperature forecast chart */}
      <section className="panel weather-forecast-panel">
        <div className="panel-heading">
          <div>
            <h3>48-Hour Temperature Forecast</h3>
            <p>
              Expected hourly temperature from the Open-Meteo forecast.
            </p>
          </div>

          <span className="record-count">
            {forecast.length} records
          </span>
        </div>

        {chartData.length > 0 ? (
          <div className="weather-chart">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart
                data={chartData}
                margin={{
                  top: 10,
                  right: 20,
                  left: 10,
                  bottom: 10,
                }}
              >
                <CartesianGrid strokeDasharray="3 3" />

                <XAxis
                  dataKey="time"
                  interval={5}
                  tick={{ fontSize: 11 }}
                />

                <YAxis
                  unit="°C"
                  tick={{ fontSize: 11 }}
                  width={55}
                />

                <Tooltip
                  labelFormatter={(_, payload) =>
                    payload?.[0]?.payload?.timestamp
                      ? formatForecastDate(
                          payload[0].payload.timestamp,
                        )
                      : ""
                  }
                  formatter={(value) => [
                    `${Number(value).toFixed(1)} °C`,
                    "Temperature",
                  ]}
                />

                <Line
                  type="monotone"
                  dataKey="temperature"
                  name="Temperature"
                  stroke="#e6a23c"
                  strokeWidth={2.5}
                  dot={false}
                  activeDot={{ r: 5 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <p className="weather-status">
            No temperature forecast is available.
          </p>
        )}
      </section>

      {/* Solar radiation forecast chart */}
      <section className="panel weather-forecast-panel">
        <div className="panel-heading">
          <div>
            <h3>Solar Radiation Forecast</h3>
            <p>
              Expected hourly solar radiation for renewable energy planning.
            </p>
          </div>
        </div>

        {chartData.length > 0 ? (
          <div className="weather-chart">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart
                data={chartData}
                margin={{
                  top: 10,
                  right: 20,
                  left: 10,
                  bottom: 10,
                }}
              >
                <CartesianGrid strokeDasharray="3 3" />

                <XAxis
                  dataKey="time"
                  interval={5}
                  tick={{ fontSize: 11 }}
                />

                <YAxis
                  unit=" W/m²"
                  tick={{ fontSize: 11 }}
                  width={65}
                />

                <Tooltip
                  labelFormatter={(_, payload) =>
                    payload?.[0]?.payload?.timestamp
                      ? formatForecastDate(
                          payload[0].payload.timestamp,
                        )
                      : ""
                  }
                  formatter={(value) => [
                    `${Number(value).toFixed(0)} W/m²`,
                    "Solar Radiation",
                  ]}
                />

                <Line
                  type="monotone"
                  dataKey="solarRadiation"
                  name="Solar Radiation"
                  stroke="#2877c7"
                  strokeWidth={2.5}
                  dot={false}
                  activeDot={{ r: 5 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <p className="weather-status">
            No solar radiation forecast is available.
          </p>
        )}
      </section>

      {/* Hourly weather table */}
      <section className="panel weather-forecast-panel">
        <div className="panel-heading">
          <div>
            <h3>Hourly Weather Forecast</h3>
            <p>
              Future environmental conditions returned by Open-Meteo.
            </p>
          </div>

          <span className="record-count">
            {forecast.length} records
          </span>
        </div>

        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Timestamp (UTC)</th>
                <th>Temperature</th>
                <th>Humidity</th>
                <th>Wind Speed</th>
                <th>Cloud Cover</th>
                <th>Precipitation</th>
                <th>Solar Radiation</th>
              </tr>
            </thead>

            <tbody>
              {forecast.map((item) => (
                <tr key={item.timestamp_utc}>
                  <td>{formatForecastDate(item.timestamp_utc)}</td>
                  <td>{item.temperature_c.toFixed(1)} °C</td>
                  <td>{item.relative_humidity_pct}%</td>
                  <td>{item.wind_speed_ms.toFixed(1)} m/s</td>
                  <td>{item.cloud_cover_pct}%</td>
                  <td>{item.precipitation_mm.toFixed(1)} mm</td>
                  <td>{item.solar_radiation_wm2.toFixed(0)} W/m²</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Data source information */}
      <div className="weather-source">
        <CloudSun size={16} />
        <span>
          Provider: {weather.source} · Last fetched {new Date(weather.retrieved_at_utc).toLocaleString()} · Fallback {weather.fallback_status === "not_used" ? "not used" : weather.fallback_status ?? "status unavailable"}. Weather forecasts are predictions, not measured generation or guaranteed operating conditions.
        </span>
      </div>
    </section>
  );
}

function WeatherCard({
  label,
  value,
  icon,
}: {
  label: string;
  value: string;
  icon: React.ReactNode;
}) {
  return (
    <article className="weather-card">
      <div className="weather-card-heading">
        <span>{label}</span>
        {icon}
      </div>

      <strong>{value}</strong>
    </article>
  );
}
