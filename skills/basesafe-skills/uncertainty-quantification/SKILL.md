---
name: uncertainty-quantification
description: Deep uncertainty analysis for ML, AI, and agentic systems. Use when confidence quality is critical to deployment safety, when calibration affects operational decisions (abstention, escalation, routing), when distinguishing aleatoric vs epistemic uncertainty, or when assessing out-of-distribution handling. Provides comprehensive analysis beyond basic calibration checks.
---

# Uncertainty Quantification Analysis

## Overview

This skill helps assess whether a model or pipeline knows when it does not know. Use it to analyze how uncertainty is represented, measured, calibrated, surfaced, and acted on across training, evaluation, and deployment.

Treat uncertainty quantification as an engineering problem, not just a modeling technique. The goal is to connect uncertainty signals to operational decisions such as abstention, escalation, fallback behavior, human review, or deployment gating.

## Analysis Depth

This skill supports both lightweight audits and comprehensive deep-dives. Calibrate your depth to the task.

**Go deep when:**
- Model confidence affects safety-critical decisions (medical, autonomous systems, security)
- Confidence scores gate human review, escalation, or automated actions
- You need to separate aleatoric from epistemic uncertainty, handle distribution shift, or produce prediction intervals
- The system requires uncertainty-aware policies (abstention, fallback, safe defaults, deployment gating)
- Adversarial or OOD robustness of confidence signals is in scope

**Stay lightweight when:**
- The ask is a quick audit or gap inventory rather than a full deployment review
- Only basic calibration metrics (ECE/MCE on clean IID data) are needed
- Model outputs are informational and no operational decisions are gated on confidence

## Quick Reference

| Action | Approach |
|--------|----------|
| Scan for UQ evidence | Manual code review + pattern search |
| Pattern search: calibration | `rg "(calibration\|temperature.*scal\|platt\|isotonic)" --type py -A 5` |
| Pattern search: uncertainty | `rg "(uncertainty\|confidence\|ensemble\|dropout)" --type py -A 5` |
| Pattern search: abstention | `rg "(abstain\|reject\|threshold\|escalat)" --type py -A 5` |
| Find config files | `rg "threshold\|confidence" --glob "*.yaml" --glob "*.json"` |
| Review method guidance | `references/methodology.md` |
| Review agent UQ framework | `references/agent-uq-framework.md` |
| Review metrics mapping | `references/tooling-matrix.md` |
| Start analysis report | `assets/analysis_report_template.md` |

## Core Workflow

### Two-step execution (analysis then formatting)

When possible, separate work into two distinct phases:

**Phase A: Analysis (can delegate to a subagent)**
- Goal: collect evidence and produce structured findings and recommendations.
- Output: a compact, structure-first artifact (not a polished report).
- Optional: bootstrap evidence with `scripts/uq_analysis.py <repo-root> --format json`.
- Include: system context (task type, inputs/outputs, decision consequence)
- Include: evidence index (file paths and short notes; include config/threshold locations)
- Include: findings list (implemented/partial/missing/unknown) with why it matters and file/path evidence
- Include: recommended approaches (1-3) and metrics to track
- Include: operational guidance (routing/abstain/escalate/fail-closed)
- Include: unknowns and assumptions

**Phase B: Report synthesis and formatting (main agent)**
- Goal: translate Phase A into the `assets/analysis_report_template.md` format.
- Requirements: preserve evidence fidelity (paths), keep recommendations prioritized, and keep scope aligned to **Analysis Depth**.

If you delegate Phase A, instruct the subagent to avoid report prose and return only the structured artifact above.

### 1. Establish the uncertainty surface

Determine:
- Prediction type: classification, regression, ranking, generation, detection, segmentation, retrieval, agent decision
- Decision consequence: low-stakes logging, user-facing recommendation, automated actuation, safety gate
- Existing uncertainty outputs: softmax scores, intervals, variances, ensemble disagreement, heuristics, refusal logic
- Failure modes: class confusion, hallucination, OOD drift, corrupted inputs, retrieval misses, prompt sensitivity

### 2. Gather repository evidence

Look for concrete evidence in code, configs, and documentation:

**Search patterns:**
```bash
# Find calibration implementations
rg "temperature.*scaling|platt.*scaling|isotonic" --type py -A 5

# Locate uncertainty estimation methods
rg "ensemble|dropout.*inference|bayesian|uncertainty" --type py -A 10

# Identify abstention/rejection logic
rg "abstain|reject|confidence.*threshold|escalate" --type py -A 5

# Find OOD detection
rg "out.*of.*distribution|ood|novelty.*detect|drift.*detect" --type py -A 5

# Check evaluation scripts for UQ metrics
rg "calibration|uncertainty|ECE|Brier" --glob "**/eval/*.py" -A 5
rg "calibration|uncertainty" --glob "**/test/*.py" -A 5

# Review configs for thresholds and policies
rg "threshold|confidence|uncertainty|abstain" --glob "*.yaml" --glob "*.json"

# Find conformal prediction
rg "conformal|coverage|prediction.*interval" --type py -A 5

# Locate model cards or documentation
rg -i "uncertainty|calibration|confidence" --glob "*model*card*" --glob "*README*"
```

**Prioritize evidence for:**
- **Methods**: ensembles, MC dropout, Bayesian approximations, Gaussian processes, conformal prediction
- **Calibration**: temperature scaling, Platt scaling, isotonic regression, reliability diagrams, ECE/Brier/NLL
- **Selective prediction**: abstain/reject options, confidence thresholds, human review triggers
- **OOD handling**: drift detection, novelty detection, corrupted-data tests, retrieval confidence
- **Operational use**: fallback logic, alerts, safe defaults, deployment gates

### 3. Classify what is present and what is missing

For each claim, separate:
- **Implemented**: visible in code, configs, metrics, or docs
- **Partially implemented**: signal exists but is not validated or operationalized
- **Missing**: method or control should exist but no evidence was found
- **Unknown**: could exist outside the repo

### 4. Recommend methods that fit the task

Match method sophistication to task requirements and current capabilities. Prefer simple, validated baselines over complex probabilistic frameworks unless complexity is justified.

**Method Selection by Task:**

| Task Type | Lightweight Baseline | When to Upgrade | Advanced Methods |
|-----------|---------------------|-----------------|------------------|
| **Classification** | Temperature scaling | Multi-class imbalance, security-critical | Conformal prediction sets, ensemble disagreement |
| **Regression** | Quantile regression | Safety-critical bounds | Conformal regression, Gaussian processes |
| **Detection/Segmentation** | Per-box confidence calibration | Pixel-level uncertainty needed | Epistemic maps via dropout, corruption robustness |
| **Generation/LLM** | Self-consistency variance | Factual grounding required | Verifier disagreement, citation-based confidence |
| **Agent pipelines** | Tool selection confidence | Multi-step uncertainty propagation | Branching probability, retrieval sufficiency scores |

**Avoid recommending:**
- Full Bayesian neural networks for simple classification (start with temperature scaling)
- Gaussian processes for high-dimensional problems (poor scaling)
- Ensemble methods without testing single-model calibration first
- Complex methods when simple ones haven't been tried

**Do recommend:**
- Conformal prediction (distribution-free, finite-sample guarantees)
- Temperature/Platt scaling (simple, effective for calibration)
- Ensemble disagreement (when multiple models already exist)
- MC dropout (when uncertainty needed without retraining)
- Prediction intervals for regression (quantile regression or conformal)
- Abstention policies with risk-coverage curves

**Specific Guidance by Task:**

**Classification:**
- Prefer calibration over raw softmax scores
- Test calibration on IID, OOD, and adversarial data
- Recommend conformal prediction for set-valued predictions with coverage guarantees
- Use ensemble disagreement only if ensemble already exists

**Regression / Forecasting:**
- Provide prediction intervals, not just point estimates
- Use conformal regression for distribution-free intervals
- Report coverage (empirical vs. nominal) and interval width
- Use CRPS (Continuous Ranked Probability Score) for probabilistic forecasts

**Detection / Segmentation:**
- Calibrate per-box or per-pixel confidence
- Provide epistemic uncertainty maps (e.g., via MC dropout)
- Test robustness to corruptions (blur, noise, occlusion)
- Recommend abstention on low-confidence regions

**Generative / LLM Systems:**
- Self-consistency: sample multiple outputs, measure variance
- Verifier disagreement: use separate models to check outputs
- Citation grounding: confidence based on retrieval quality
- Abstention policy: refuse when uncertainty exceeds threshold
- Token-level uncertainty: attention entropy, logit variance

**Agent Pipelines:**

> See `references/agent-uq-framework.md` for method selection, implementation guidance, and validation for agent and multi-turn pipeline UQ.

### 5. Test uncertainty under adversarial conditions

Test whether uncertainty signals can detect adversarial manipulation or OOD scenarios. Uncertainty estimates may behave differently when the model is under attack.

**Key Tests**:
- **Calibration Under Attack**: Does confidence remain well-calibrated on adversarial examples?
- **Uncertainty as Attack Detector**: Can uncertainty signals detect adversarial inputs?
- **Attack-Specific Patterns**: Different attacks produce different uncertainty signatures
- **OOD Detection for Agents**: Use uncertainty to detect out-of-distribution scenarios in agentic systems
- **Distribution Shift**: Does uncertainty increase appropriately under shift?

**Risk Levels**:
- **Critical**: Model confident on misclassified adversarial examples, no OOD detection
- **High**: Poor calibration under attack, uncertainty doesn't increase on adversarial data
- **Medium**: Uncertainty increases on adversarial data but not sufficiently for detection
- **Low**: Well-calibrated under attack, uncertainty effectively detects adversarial inputs

**Detailed methodology**: See `references/adversarial-uq.md` for complete testing protocols, metrics, and integration guidance.

### 6. Produce an actionable report

Use `assets/analysis_report_template.md` as your structure. See **Required Output Shape** below for the sections to include and how to calibrate them to analysis depth.

## Required Output Shape

Structure every UQ analysis using `assets/analysis_report_template.md`. The sections below are always required; tailor depth and detail to the analysis scope.

### Executive Summary
- Overall assessment of current UQ maturity
- Highest-risk gaps
- Whether existing confidence signals are decision-usable

### Evidence-Based Findings
- Specific methods or gaps with file/path evidence
- Classify each item: implemented, partially implemented, missing, or unknown
- Distinguish uncertainty estimation, calibration, and policy use

### Recommended Approaches
- 1–3 prioritized approaches matched to the model and deployment context
- Why each approach fits better than alternatives
- What metrics should improve if implemented correctly

### Tooling and Implementation Notes
- Concrete libraries or patterns to use (see `references/tooling-guide.md`)
- Integration points and interpretation notes
- Justify lightweight baselines vs. more complex approaches

### Operational Guidance
- How to route uncertain outputs
- Where to abstain, escalate, retry, or fail closed
- Which metrics should be monitored in production

### Unknowns and Assumptions
- Evidence gaps that limit conclusions
- Aspects that could not be assessed from the repository alone

**For deep analyses**, also include:
- Adversarial uncertainty analysis results (see `references/adversarial-uq.md`)
- An implementation roadmap (use `assets/roadmap-template.md`)

## Red Flags

Escalate concern when you find:

- Confidence scores used as probabilities without calibration evidence
- Thresholds chosen without risk-coverage or validation analysis
- Softmax maximum treated as uncertainty with no OOD testing
- No abstention or escalation path for high-uncertainty cases
- Retrieval or tool-use pipelines with no measure of evidence sufficiency
- Calibration only reported on IID validation data despite known domain shift
- Bayesian or ensemble methods claimed in docs but absent in code
- Generative systems using style or verbosity as a proxy for certainty
- Confidence-based access control without adversarial calibration testing
- Safety-critical decisions gated by uncalibrated confidence

## Tooling Recommendations

**Comprehensive tooling guide**: See `references/tooling-guide.md` for detailed information on:
- Calibration tools (NetCal, scikit-learn, uncertainty-toolbox)
- Conformal prediction (MAPIE, crepes)
- Bayesian/ensemble methods (MC Dropout, TensorFlow Probability, Pyro)
- OOD detection (PyOD, ADBench, torch-uncertainty)
- Metrics and evaluation tools
- Agent/LLM-specific methods (self-consistency, logit variance, attention entropy)
- Adversarial testing (ART, Foolbox, WILDS, ImageNet-C)

## Practical Guidance

### Evidence Over Aspiration
- Prefer repository evidence over documentation claims
- If code doesn't show calibration, it's not calibrated
- If thresholds are hardcoded without validation, they're arbitrary

### Simple Before Complex
- Temperature scaling before Bayesian neural networks
- Quantile regression before Gaussian processes
- Single-model calibration before ensembles
- Validate baseline before adding complexity

### Separation of Concerns
- Uncertainty estimation (method produces uncertainty signal)
- Calibration (uncertainty signal is accurate)
- Policy (how to act on uncertainty signal)
- Good UQ without a response policy still leaves risk

### State Uncertainty Explicitly
- If evidence is thin, say "insufficient evidence to assess"
- Distinguish "not implemented" from "implemented but not validated"
- Note when UQ methods are claimed in docs but absent in code

### Connect to Operations
- Uncertainty must connect to decisions (abstain, escalate, retry, fail closed)
- Calibration without operational use is a vanity metric
- Recommend specific policies: "Escalate when confidence < 0.7"

## Common Patterns

### Pattern 1: Confidence Used, Not Calibrated
**Issue**: Uncalibrated softmax used for decisions | **Risk**: HIGH  
**Recommendation**: Add temperature scaling + validation

### Pattern 2: Calibration on IID Only
**Issue**: Calibration may not hold under distribution shift | **Risk**: MEDIUM-HIGH  
**Recommendation**: Test calibration on shifted/corrupted data

### Pattern 3: Ensemble Without Disagreement
**Issue**: Wasted opportunity for uncertainty quantification | **Risk**: LOW  
**Recommendation**: Report ensemble disagreement as epistemic uncertainty

### Pattern 4: Thresholds Without Validation
**Issue**: Arbitrary threshold without risk-coverage analysis | **Risk**: MEDIUM  
**Recommendation**: Plot risk-coverage curve, choose validated threshold

### Pattern 5: Generation Without Uncertainty
**Issue**: No way to detect unreliable outputs | **Risk**: HIGH for factual domains  
**Recommendation**: Add self-consistency variance + abstention policy

**Detailed pattern analysis**: See `references/methodology.md`

## Conclusion

Uncertainty quantification is not about choosing the most sophisticated method - it's about connecting uncertainty signals to operational decisions in a reliable, validated way. Start simple, validate thoroughly, and add complexity only when justified by deployment requirements.

**Critical Addition**: Always test uncertainty under adversarial conditions and distribution shift, not just on IID validation data. Models must know when they don't know, especially when under attack or encountering novel scenarios.
