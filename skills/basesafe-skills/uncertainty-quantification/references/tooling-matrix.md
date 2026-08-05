# UQ Tooling and Metrics Matrix

## Core metrics by task

| Task | Core Metrics | What they answer |
|------|--------------|------------------|
| Classification | ECE, MCE, Brier score, NLL, AUROC for selective prediction | Are confidence scores calibrated and decision-useful? |
| Regression | RMSE, MAE, PICP, MPIW, CRPS | Are intervals accurate and appropriately wide? |
| Forecasting | CRPS, coverage by horizon, quantile loss | Does uncertainty remain valid over time and horizon? |
| Detection | confidence vs IoU, per-class ECE, OOD slices | Are detections calibrated and robust? |
| Segmentation | pixel calibration, uncertainty maps, corruption robustness | Where is the model uncertain spatially? |
| Retrieval / RAG | answerability, retrieval recall, citation support rate | Is there enough evidence to answer confidently? |
| LLM / agent | self-consistency variance, judge disagreement, refusal precision/recall | Does the system know when to abstain or escalate? |

## Common methods and tools

| Method | Best for | Libraries / tooling | Notes |
|--------|----------|---------------------|-------|
| Temperature scaling | Classification calibration | `netcal`, custom PyTorch / sklearn code | Cheap and strong baseline |
| Isotonic regression | Flexible calibration | `scikit-learn` | Works well with enough calibration data |
| Platt scaling | Binary classification | `scikit-learn` | Simple baseline |
| Deep ensembles | Epistemic uncertainty | native training loops, PyTorch Lightning, Ray Tune | Strong practical baseline, higher compute |
| MC dropout | Approximate epistemic uncertainty | native PyTorch / TensorFlow | Easy retrofit if dropout already exists |
| Bayesian last layer | Moderate-cost probabilistic upgrade | Pyro, PyMC, Laplace | Good compromise for deep nets |
| Gaussian processes | Small data, structured uncertainty | GPyTorch, scikit-learn | Hard to scale broadly |
| Conformal prediction | Coverage guarantees | `mapie`, `nonconformist`, custom code | Very practical for deployment |
| OOD detection | Distribution shift | `pytorch-ood`, embedding distance baselines | Must be evaluated on relevant shift |
| Adversarial / corruption testing | Robustness-linked uncertainty | ART, robustness benchmarks | Use to test failure sensitivity |

## Installation snippets

```bash
pip install scikit-learn mapie netcal
pip install torch pyro-ppl laplace-torch
pip install tensorflow tensorflow-probability
pip install pytorch-ood adversarial-robustness-toolbox
```

## Interpretation notes

- Lower ECE is better, but low ECE alone does not guarantee good decisions.
- Coverage should be checked together with interval width. Trivial wide intervals are not useful.
- Ensemble disagreement is only useful if the members are meaningfully diverse.
- Refusal or abstention should be judged by both safety benefit and unnecessary deferral rate.
- For agentic systems, uncertainty must be tied to routing or control policy, not just exposed in logs.

