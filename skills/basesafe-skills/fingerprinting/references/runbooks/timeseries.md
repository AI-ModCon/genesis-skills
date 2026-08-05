# Time Series Runbook

Use this runbook for forecasting, sequential sensor prediction, anomaly detection over time, or temporal decision systems.

## Inspect

- rolling-window generation and horizon setup
- split strategy to prevent leakage across time
- feature engineering for lags, seasonality, and exogenous inputs
- forecast serving logic and update cadence
- drift or temporal-regime monitoring

## Capture

- prediction target and horizon
- modality: timeseries or sensor stream
- model family: statistical, transformer, recurrent, hybrid
- evaluation metrics by horizon or regime
- evidence of interval forecasts or uncertainty outputs

## Common Hooks

- attack surface: temporal drift, spoofed inputs, stale retraining
- uncertainty hooks: prediction intervals, CRPS, coverage by horizon
- explainability hooks: lag importance, regime-specific diagnostics

## Typical Unknowns

- retraining cadence in production
- operational thresholds by horizon
- missing-data handling under deployment conditions

