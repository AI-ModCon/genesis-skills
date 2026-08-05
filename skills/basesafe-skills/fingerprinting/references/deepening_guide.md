# Deepening Guide

This guide replaces hard-coded routing. Use it to decide which runbooks to load after producing the level-1 fingerprint.

## How to Use

1. Produce an initial taxonomy classification.
2. Identify the strongest signals in the repository.
3. Load only the runbooks that will materially improve the fingerprint.

## Common Deepening Patterns

### Vision

Load `${CLAUDE_SKILL_DIR}/references/runbooks/vision.md` when you see:
- image or video datasets
- torchvision, detectron, mmcv, monai, cv2
- bounding boxes, masks, augmentations, dataloaders for images

### NLP / RAG

Load `${CLAUDE_SKILL_DIR}/references/runbooks/nlp_rag.md` when you see:
- text generation, summarization, chat, QA
- prompt templates or system prompts
- vector stores, retrievers, rerankers, citation logic

### Tabular

Load `${CLAUDE_SKILL_DIR}/references/runbooks/tabular.md` when you see:
- dataframes, feature pipelines, joins, encoders, imputers
- sklearn, xgboost, lightgbm, catboost

### Time Series

Load `${CLAUDE_SKILL_DIR}/references/runbooks/timeseries.md` when you see:
- forecasting windows, rolling splits, horizon metrics
- telemetry, sensor streams, temporal feature engineering

### Audio

Load `${CLAUDE_SKILL_DIR}/references/runbooks/audio.md` when you see:
- waveform or spectrogram preprocessing
- speech, speaker, transcription, acoustic modeling

### Retrieval / Recommendation

Load `${CLAUDE_SKILL_DIR}/references/runbooks/retrieval_recsys.md` when you see:
- vector indexes, ANN search, ranking metrics
- candidate generation, reranking, click or relevance logic

### RL / Control

Load `${CLAUDE_SKILL_DIR}/references/runbooks/rl_control.md` when you see:
- environments, simulators, policies, rewards, rollouts
- offline RL, safety constraints, controllers

### Multimodal

Load `${CLAUDE_SKILL_DIR}/references/runbooks/multimodal.md` when:
- multiple modalities are first-class parts of the model
- fusion, cross-attention, image-text or audio-text alignment appears

### Serving / Security

Load `${CLAUDE_SKILL_DIR}/references/runbooks/serving_security.md` when you see:
- APIs, web apps, streaming inference, queues, background workers
- model serving infra, gateways, auth, rate limiting, observability

## Practical Rule

If uncertain, prefer:
- one primary modality runbook
- one serving or platform runbook if deployment matters
- cross-cutting concerns for attacks / UQ / explainability

Avoid loading 5-6 runbooks unless the system is genuinely multi-component.

