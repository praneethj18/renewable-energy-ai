from pathlib import Path
import json

PROJECT_ROOT = Path(__file__).resolve().parents[2]

METRICS_PATH = (
    PROJECT_ROOT
    / "models"
    / "real_world_weather"
    / "evaluation_report.json"
)

OUTPUT_PATH = (
    PROJECT_ROOT
    / "models"
    / "real_world_weather"
    / "evaluation_report.md"
)


def main():
    if not METRICS_PATH.exists():
        raise FileNotFoundError(
            f"Evaluation metrics not found: {METRICS_PATH}"
        )

    with METRICS_PATH.open("r", encoding="utf-8") as file:
        report = json.load(file)

    results = report.get("results")
    if not isinstance(results, dict) or not results:
        raise ValueError(
            "Expected a non-empty 'results' object in evaluation_report.json."
        )

    lines = [
        "# Real-World Weather-Informed Energy Forecasting Evaluation",
        "",
        "## Dataset and Provenance",
        "",
        f"- Energy source: {report.get('energy_source', 'OPSD Germany')}",
        f"- Weather source: {report.get('weather_source', 'Open-Meteo ERA5')}",
        f"- Dataset: {report.get('dataset', 'Not specified')}",
        "- Energy measurements: German national/regional solar generation, wind generation, and electricity demand",
        "- Weather location: Berlin, Germany",
        "- Data granularity: Hourly",
        "- Evaluation type: Chronological retrospective one-step evaluation",
        "- Energy and weather records were joined using UTC timestamps.",
        "- Limitation: Berlin weather is not representative of the entire German energy system.",
        "- Limitation: National/regional energy data does not represent an individual renewable-energy facility.",
        "",
        "## Evaluation Method",
        "",
        "- Separate Random Forest models for solar generation, wind generation, and demand.",
        "- Chronological train-test evaluation.",
        "- Comparison against a same-hour previous-day baseline.",
        "- Metrics: Mean Absolute Error (MAE) and Root Mean Squared Error (RMSE), measured in MW.",
        "- This is retrospective evaluation, not validated operational forecasting.",
        "",
        "## Results",
        "",
        "| Target | Train Records | Test Records | Model MAE (MW) | Baseline MAE (MW) | Model RMSE (MW) | Baseline RMSE (MW) |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]

    for target, values in results.items():
        model = values["model"]
        baseline = values["same_hour_previous_day_baseline"]

        lines.append(
            f"| {target} "
            f"| {values['training_records']} "
            f"| {values['test_records']} "
            f"| {model['mae_mw']:.2f} "
            f"| {baseline['mae_mw']:.2f} "
            f"| {model['rmse_mw']:.2f} "
            f"| {baseline['rmse_mw']:.2f} |"
        )

    lines.extend([
        "",
        "## Interpretation",
        "",
        "- **Solar:** The model has lower RMSE but higher MAE than the baseline. It does not outperform the baseline on both metrics.",
        "- **Wind:** The model outperforms the baseline on both MAE and RMSE.",
        "- **Demand:** The model outperforms the baseline on both MAE and RMSE.",
        "",
        "## Limitations and Deployment Readiness",
        "",
        "- Weather inputs are historical observations, which may not be available for future forecast timestamps.",
        "- Operational forecasts must use weather forecasts available at prediction time.",
        "- Berlin weather is a single-location proxy for German national/regional energy measurements.",
        "- The evaluation is a retrospective one-step experiment, not a validated operational forecast.",
        "- A separate chronological validation set and evaluation across multiple forecast horizons are still needed.",
        "- The results do not demonstrate individual-facility forecasting accuracy.",
        "",
        "## Conclusion",
        "",
        "The weather-informed models show different levels of performance against the previous-day baseline. "
        "Wind and demand improve on both reported metrics, while solar improves on RMSE but not MAE. "
        "These results are preliminary and do not establish operational readiness. "
        "Forecast-time weather inputs, further validation, and horizon-specific testing remain necessary.",
        "",
    ])

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text("\n".join(lines), encoding="utf-8")

    print("Weather-informed evaluation report created successfully.")
    print(f"Metrics: {METRICS_PATH}")
    print(f"Report: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()