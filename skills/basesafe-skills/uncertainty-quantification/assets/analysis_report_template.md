# Uncertainty Quantification Analysis Report

**System / Model:** [Name]  
**Analysis Date:** [YYYY-MM-DD]  
**Analyst:** [Name]  

---

## Executive Summary

[2-3 paragraphs summarizing current uncertainty posture, decision risk, and the most important gaps.]

**Overall Assessment:** [Mature / Partial / Minimal / Absent]

**Top Risks:**
1. [Highest-priority issue]
2. [Second issue]
3. [Third issue]

---

## System Context

- **Task type:** [classification / regression / detection / generation / retrieval / agent]
- **Input modality:** [text / image / audio / multimodal / tabular / time-series]
- **Output type:** [label / score / interval / text / action / ranking]
- **Decision consequence:** [low / medium / high]
- **Evidence reviewed:** [key files, tests, configs, docs]

---

## Current UQ Posture

### Implemented Signals
- [Existing confidence score, interval, disagreement metric, refusal logic, etc.]

### Calibration Evidence
- [ECE, Brier, NLL, reliability diagrams, temperature scaling, or "none found"]

### OOD / Drift / Corruption Handling
- [OOD detectors, stress tests, corruption benchmarks, or "none found"]

### Operational Use of Uncertainty
- [abstention, escalation, review queue, retry policy, fallback routing, or "none found"]

---

## Findings

### Finding 1: [Short title]

**Assessment:** [Implemented / Partial / Missing / Unknown]  
**Why it matters:** [Risk or impact]  
**Evidence:** [file paths, configs, tests, or excerpt summary]  
**Recommended action:** [Concrete next step]

### Finding 2: [Short title]

[Repeat as needed]

---

## Recommended Approaches

### Approach 1: [Method or experiment]

**Fit:** [Why it matches this system]  
**What it measures:** [epistemic / aleatoric / calibration / OOD / selective prediction]  
**Metrics to track:** [ECE, Brier, AUROC, coverage, interval width, etc.]  
**Expected outcome:** [How decisions improve]

### Approach 2: [Method or experiment]

### Approach 3: [Method or experiment]

---

## Tooling Notes

### Recommended Tool or Library: [Name]

**Install:**
```bash
pip install [package]
```

**Integration Point:** [training / evaluation / inference / monitoring]  
**Interpretation Notes:** [how to read the output correctly]  
**Caveats:** [main assumptions or limitations]

---

## Implementation Roadmap

### Immediate
- [Fast baseline or instrumentation step]

### Short-Term
- [Evaluation or calibration work]

### Medium-Term
- [More structural model or platform changes]

---

## Production Monitoring

- [Metric 1]
- [Metric 2]
- [Metric 3]

---

## Unknowns and Assumptions

- [Missing artifact or assumption]
- [Open question]

