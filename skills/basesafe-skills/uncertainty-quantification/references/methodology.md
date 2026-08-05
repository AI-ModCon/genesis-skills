# Uncertainty Quantification Methodology

This reference supports repository-level UQ analysis. It is meant to help choose methods that match the task, not to force every system into the same probabilistic toolkit.

## 1. What to look for first

Start by answering:

1. What prediction or decision is the system making?
2. What harm occurs if confidence is wrong?
3. Is there already a confidence signal, and is it calibrated?
4. Does the system have an abstain, escalate, or fallback path?
5. Has uncertainty been evaluated under distribution shift or corrupted inputs?

If the answer to 3-5 is mostly "no", the primary gap is usually not model complexity. It is missing evaluation discipline and missing operational controls.

## 2. UQ dimensions

### Aleatoric uncertainty

Irreducible uncertainty from noisy, ambiguous, or incomplete observations.

Typical signals:
- label ambiguity
- occlusion, blur, sensor noise
- stochastic environments
- ambiguous prompts or incomplete context

Useful methods:
- heteroscedastic regression heads
- quantile regression
- predictive intervals
- conformal methods with representative calibration data

### Epistemic uncertainty

Reducible uncertainty from limited knowledge, sparse coverage, model misspecification, or unfamiliar inputs.

Typical signals:
- sparse regions of feature space
- rare classes
- novel environments
- prompt or task variants not seen during tuning

Useful methods:
- deep ensembles
- MC dropout
- Bayesian last-layer approximations
- Gaussian processes for small or structured problems
- distance- or density-based OOD methods

### Distributional / deployment uncertainty

Uncertainty caused by a mismatch between development conditions and real use.

Typical signals:
- domain drift
- temporal shift
- changed class balance
- new retrieval corpus
- production prompts unlike evaluation prompts

Useful methods:
- OOD detection
- corruption benchmarks
- stress tests
- drift monitoring
- uncertainty-conditioned routing

## 3. Distinguish these three layers

### Estimation

How the model produces uncertainty signals:
- probabilities
- variances
- intervals
- disagreement
- conformal sets

### Calibration

Whether those signals correspond to reality:
- does 0.8 confidence mean about 80% correctness?
- do 90% intervals cover about 90% of outcomes?

### Policy

What the system does with uncertainty:
- abstain
- escalate to human review
- request more context
- use a fallback model
- refuse to act

Many repositories have estimation but not calibration, or calibration but no policy.

## 4. Evidence checklist

Look for evidence in the following order:

1. Inference code that emits confidence, intervals, or uncertainty scores
2. Evaluation code computing calibration or coverage metrics
3. Thresholding logic for rejection, abstention, or fallback
4. Stress-test code for OOD, corruption, prompt variation, or adversarial perturbation
5. Monitoring code that logs uncertainty in production
6. Documentation claiming UQ behavior

Docs without code or metrics should be treated as partial evidence.

## 5. Task-specific method selection

### Classification

Strong first-pass choices:
- temperature scaling
- reliability diagrams
- ECE, MCE, Brier score, NLL
- selective prediction with risk-coverage curves
- deep ensembles if higher-stakes and compute allows

### Regression and forecasting

Strong first-pass choices:
- prediction interval coverage probability
- mean interval width
- conformal regression
- CRPS for probabilistic forecasts
- quantile regression for asymmetric risk

### Detection and segmentation

Strong first-pass choices:
- per-class and per-box calibration
- confidence-vs-IoU analysis
- ensemble or MC-dropout variance maps
- corruption robustness and OOD slices

### Retrieval, RAG, and ranking

Strong first-pass choices:
- retrieval score calibration
- evidence sufficiency heuristics
- answerability / abstention evaluation
- disagreement between retrieved evidence and final answer

### LLM and agent systems

Strong first-pass choices:
- self-consistency disagreement
- verifier or judge disagreement
- citation grounding checks
- retrieval sufficiency and tool-result sufficiency checks
- escalation policies for low-support outputs

Do not pretend token probabilities alone are reliable uncertainty estimates for end-task correctness.

## 6. Common anti-patterns

- Using raw softmax as calibrated probability without testing
- Reporting only average confidence, not correctness-conditioned confidence
- Treating an ensemble as sufficient without measuring calibration or OOD gains
- Evaluating on IID validation only, despite obvious deployment shift
- Calling a refusal policy "UQ" without measuring its precision and recall
- Claiming Bayesian methods from comments or design docs with no implementation

## 7. What a good first-pass recommendation looks like

A useful UQ recommendation:
- names the concrete gap
- matches the method to the task
- includes metrics
- defines how outputs affect operational decisions
- states unknowns and assumptions

Example:

"The repository emits class probabilities but no calibration evidence and no abstention path. Start with temperature scaling on a held-out calibration split, report ECE/Brier/NLL, then introduce a risk-coverage policy that routes low-confidence predictions to review."

