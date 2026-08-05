# Fingerprinting Taxonomy

This reference defines the controlled vocabulary used for first-pass repository fingerprinting. Prefer these terms so that later analysis stays consistent.

## 1. Repository Type

Use the best fit:
- `research codebase`
- `training pipeline`
- `inference service`
- `evaluation harness`
- `agent application`
- `retrieval pipeline`
- `demo or prototype`
- `multi-component platform`

## 2. Task Types

Choose one or more:
- `classification`
- `regression`
- `object detection`
- `segmentation`
- `generation`
- `summarization`
- `retrieval`
- `ranking`
- `recommendation`
- `forecasting`
- `anomaly detection`
- `control`
- `simulation`
- `embedding`

Boundary guidance:
- If a system retrieves and then answers, classify both `retrieval` and the downstream task such as `generation` or `summarization`.
- If a system predicts actions in an environment, prefer `control` and optionally `simulation`.

## 3. Input Modalities

Choose one or more:
- `image`
- `video`
- `text`
- `audio`
- `tabular`
- `timeseries`
- `sensor data`
- `code`
- `multimodal`

Use `multimodal` only when multiple primary modalities materially shape model behavior.

## 4. Output Modalities

Choose one or more:
- `label`
- `score`
- `scalar`
- `vector`
- `text`
- `image`
- `audio`
- `bounding box`
- `mask`
- `ranking`
- `action`
- `simulation state`
- `embedding`

## 5. Model Family

Use the strongest supported category:
- `transformer`
- `cnn`
- `resnet`
- `unet`
- `rnn`
- `lstm`
- `gbdt`
- `random forest`
- `svm`
- `gaussian process`
- `diffusion`
- `policy network`
- `retriever-reranker`
- `hybrid pipeline`

Use `hybrid pipeline` when orchestration across multiple models matters more than any single component.

## 6. Framework / Stack

Common values:
- `pytorch`
- `tensorflow`
- `jax`
- `keras`
- `sklearn`
- `xgboost`
- `lightgbm`
- `onnx`
- `huggingface`
- `langchain`
- `llamaindex`
- `ray`
- `triton`

## 7. Training Regime

Choose one or more:
- `supervised`
- `unsupervised`
- `self-supervised`
- `reinforcement`
- `fine-tuned`
- `retrieval-augmented`
- `inference-only`

## 8. Data Characteristics

Use only when supported by evidence:
- `public dataset`
- `proprietary dataset`
- `pii`
- `phi`
- `biometrics`
- `medical imaging`
- `streaming data`
- `synthetic data`
- `human feedback`

## 9. Serving Pattern

Choose one or more:
- `batch`
- `api`
- `webapp`
- `edge`
- `mobile`
- `offline notebook`
- `inference service`
- `human-in-the-loop`

## 10. High-Value Signals

Use sparingly:
- `multimodal`
- `rag`
- `tool-using`
- `safety-critical`
- `real-time`
- `simulator-dependent`
- `evaluation-heavy`

## 11. Confidence Guidance

Use confidence bands consistently:
- `high`: directly supported by code, configs, tests, or repeated documentation
- `medium`: supported by some direct evidence but not fully corroborated
- `low`: inferred from weak or incomplete evidence

