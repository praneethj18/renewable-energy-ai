# Real-World Energy Forecasting Evaluation

## Dataset

- Source: Open Power System Data (OPSD)
- Geographic scope: Germany
- Measurements: Actual solar generation, wind generation, and electricity demand
- Original period: January 2015 to September 2020
- Data granularity: Hourly
- Data type: National/regional energy measurements, not facility-level measurements

## Evaluation Method

- Chronological 80/20 train-test split
- Random Forest regression models
- Comparison against a same-hour previous-day baseline
- Metrics: Mean Absolute Error (MAE) and Root Mean Squared Error (RMSE)

## Results

| Target | Model MAE (MW) | Model RMSE (MW) | Baseline MAE (MW) | Baseline RMSE (MW) |
|---|---:|---:|---:|---:|
| solar_generation_mw | 1137.26 | 2332.61 | 1148.77 | 2479.83 |
| wind_generation_mw | 6746.93 | 8804.20 | 7096.47 | 9400.50 |
| demand_mw | 1562.51 | 2425.59 | 4133.15 | 6320.69 |

## Limitations

- The models use time-based features and historical energy measurements.
- Weather features have not yet been incorporated into these models.
- Results apply to the selected German regional dataset.
- The results do not demonstrate individual renewable-facility forecasting accuracy.
- Performance should be reassessed when additional features and forecasting horizons are introduced.

## Conclusion

All three models were evaluated against a simple baseline on a chronological test period. The recorded metrics provide an initial real-world benchmark; further evaluation is needed before considering deployment.
