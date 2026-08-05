# Tabular Runbook

Use this runbook for structured-data models, feature pipelines, or classical ML systems.

## Inspect

- schema definitions, feature stores, joins, and preprocessing code
- training and validation split logic
- model choice and hyperparameter configuration
- batch scoring or inference APIs
- monitoring and retraining logic

## Capture

- task type: classification, regression, ranking, anomaly detection
- feature engineering patterns
- framework: sklearn, xgboost, lightgbm, catboost
- split strategy and leakage risk indicators
- evidence of calibration and thresholding

## Common Hooks

- attack surface: data leakage, feature manipulation, privacy inference
- uncertainty hooks: calibration, conformal prediction, risk-coverage
- explainability hooks: SHAP, feature importance, counterfactuals

## Typical Unknowns

- provenance of joined data sources
- training-serving skew controls
- fairness-sensitive features
- threshold governance

