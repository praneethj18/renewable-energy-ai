from typing import Any
import math
from datetime import datetime, timezone

from sqlalchemy import select

from app.db.database import SessionLocal
from app.db.models import Asset, Measurement


def performance_anomaly_node(
    state: dict[str, Any],
) -> dict[str, Any]:
    """Detect suspicious generation and demand values."""

    anomalies = []

    generation = state.get("generation_forecast_mw", [])
    demand = state.get("demand_forecast_mw", [])

    asset_status = state.get("asset_status", {})

    # Check asset availability
    if asset_status.get("inactive_assets", 0) > 0:
        anomalies.append({
            "type": "inactive_assets",
            "severity": "high",
            "description": (
                f"{asset_status['inactive_assets']} asset(s) "
                "are marked inactive."
            ),
        })

    # Validate generation forecast values
    for index, value in enumerate(generation):
        if not math.isfinite(float(value)) or float(value) < 0:
            anomalies.append({
                "type": "invalid_generation",
                "severity": "high",
                "timestep": index,
                "value": str(value),
                "description": (
                    "Generation forecast is negative or non-finite."
                ),
            })

    # Validate demand forecast values
    for index, value in enumerate(demand):
        if not math.isfinite(float(value)) or float(value) < 0:
            anomalies.append({
                "type": "invalid_demand",
                "severity": "high",
                "timestep": index,
                "value": str(value),
                "description": (
                    "Demand forecast is negative or non-finite."
                ),
            })

    # Flag a large generation-demand imbalance for review
    if generation and demand:
        if len(generation) == len(demand):
            for index, (gen, load) in enumerate(
                zip(generation, demand)
            ):
                gen = float(gen)
                load = float(load)

                if (
                    math.isfinite(gen)
                    and math.isfinite(load)
                    and load > 0
                    and gen < load * 0.25
                ):
                    anomalies.append({
                        "type": "generation_demand_imbalance",
                        "severity": "medium",
                        "timestep": index,
                        "generation_mw": gen,
                        "demand_mw": load,
                        "description": (
                            "Forecast generation is below 25% "
                            "of forecast demand."
                        ),
                    })

    forecast_timestamps = state.get("generation_forecast_timestamps", [])
    parsed_timestamps = []
    for forecast_index, value in enumerate(forecast_timestamps):
        try:
            timestamp = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            if timestamp.tzinfo is not None and timestamp.utcoffset() is not None:
                parsed_timestamps.append((forecast_index, timestamp.astimezone(timezone.utc)))
        except (TypeError, ValueError, OverflowError):
            continue

    comparisons = []
    comparison_status = "insufficient_data"
    threshold_mw = None
    if parsed_timestamps:
        try:
            with SessionLocal() as db:
                rows = db.execute(
                    select(Measurement, Asset.asset_type)
                    .join(Asset, Asset.id == Measurement.asset_id)
                    .where(
                        Measurement.timestamp.in_([timestamp for _, timestamp in parsed_timestamps]),
                        Asset.is_active.is_(True),
                        Asset.asset_type.in_(("solar", "wind")),
                    )
                ).all()

            latest_by_asset_and_time = {}
            for measurement, asset_type in rows:
                observed_at = measurement.timestamp
                if observed_at.tzinfo is None or observed_at.utcoffset() is None:
                    observed_at = observed_at.replace(tzinfo=timezone.utc)
                key = (
                    observed_at.astimezone(timezone.utc).isoformat(),
                    measurement.asset_id,
                )
                existing = latest_by_asset_and_time.get(key)
                if existing is None or measurement.id > existing[0].id:
                    latest_by_asset_and_time[key] = (measurement, asset_type)

            evaluation = (
                state.get("agent_results", {})
                .get("generation_forecasting", {})
                .get("evaluation_metrics", {})
            )
            heldout_mae = [
                evaluation.get(target, {}).get("model", {}).get("mae_mw")
                for target in ("solar", "wind")
            ]
            usable_mae = [float(value) for value in heldout_mae if isinstance(value, (int, float)) and math.isfinite(float(value))]
            if usable_mae:
                threshold_mw = max(0.2, 3 * sum(usable_mae))

            for index, timestamp in parsed_timestamps:
                timestamp_key = timestamp.isoformat()
                observed = [
                    (item, asset_type)
                    for (recorded_time, _), (item, asset_type) in latest_by_asset_and_time.items()
                    if recorded_time == timestamp_key
                ]
                if not observed:
                    continue

                actual_generation = sum(float(item.generation_mw) for item, _ in observed)
                predicted_generation = (
                    float(generation[index])
                    if index < len(generation) and math.isfinite(float(generation[index]))
                    else None
                )
                if predicted_generation is None:
                    continue

                deviation = actual_generation - predicted_generation
                comparison = {
                    "timestamp_utc": timestamp_key,
                    "actual_generation_mw": round(actual_generation, 4),
                    "forecast_generation_mw": round(predicted_generation, 4),
                    "deviation_mw": round(deviation, 4),
                }
                comparisons.append(comparison)

                if threshold_mw is not None and abs(deviation) > threshold_mw:
                    comparison["investigation_status"] = "review_required"
                    anomalies.append({
                        "type": "generation_performance_deviation",
                        "severity": "high" if abs(deviation) > 2 * threshold_mw else "medium",
                        **comparison,
                        "threshold_mw": round(threshold_mw, 4),
                        "description": (
                            f"Recorded renewable generation differs from the forecast by "
                            f"{abs(deviation):.2f} MW, above the {threshold_mw:.2f} MW screening threshold. "
                            "Review the measurement and forecast; this is not a confirmed equipment fault."
                        ),
                    })

            comparison_status = (
                "available"
                if comparisons and threshold_mw is not None
                else "threshold_unavailable"
                if comparisons
                else "no_aligned_measurements"
            )
        except Exception as exc:
            comparison_status = "unavailable"
            comparison_error = str(exc)
        else:
            comparison_error = None
    else:
        comparison_error = "No timezone-aware generation forecast timestamps were available."

    status = (
        "attention_required"
        if anomalies
        else "normal"
        if comparisons and threshold_mw is not None
        else "insufficient_data"
    )
    summary = {
        "status": status,
        "anomaly_count": len(anomalies),
        "anomalies": anomalies,
        "measurement_comparison": {
            "status": comparison_status,
            "matched_timestamps": len(comparisons),
            "screening_threshold_mw": threshold_mw,
            "threshold_source": "three times summed held-out model MAE" if threshold_mw is not None else "unavailable",
            "comparisons": comparisons,
            "message": comparison_error or (
                "No stored asset measurements align exactly with forecast timestamps."
                if not comparisons
                else (
                    "Screening threshold is derived from held-out errors for models trained "
                    "on synthetic data; any finding requires investigation and is not a confirmed equipment fault."
                )
            ),
        },
        "analysis_scope": (
            "Forecast-value validation, generation-demand imbalance, and aligned actual-versus-forecast screening"
        ),
    }

    return {
        "anomalies": anomalies,
        "performance_analysis": summary,
        "agent_results": {
            "performance_anomaly": {
                "status": summary["status"],
                "anomaly_count": len(anomalies),
                "measurement_comparison_status": comparison_status,
                "matched_timestamps": len(comparisons),
            }
        },
        "execution_trace": [
            f"performance_anomaly:{summary['status']}"
        ],
    }
