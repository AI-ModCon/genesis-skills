---
name: fingerprinting
description: Classify unfamiliar AI/ML repositories into a structured taxonomy, gather evidence for the classification, and identify cross-cutting concerns that inform follow-on safety analysis. Use when you need a normalized fingerprint of a model or system before deeper security, uncertainty, or explainability review.
---

# Repository Fingerprinting

## Overview

This skill turns an unfamiliar AI or ML repository into a structured fingerprint that answers:

- What kind of system is this?
- What evidence supports that classification?
- Which deeper questions matter next?

The fingerprint follows a consistent taxonomy for task, modality, model family, training style, and serving pattern. It identifies cross-cutting concerns (attack surfaces, uncertainty hooks, explainability requirements) and recommends appropriate follow-on analyses.

This skill is intentionally taxonomy-first and routing-light. It preserves the fingerprinting taxonomy and domain runbooks, but leaves the decision about which runbooks to load to the LLM agent rather than hard-coded dispatch logic.

## Quick Reference

| Action                                     | Command / File                                                       |
|--------------------------------------------|----------------------------------------------------------------------|
| Scan repository for likely evidence        | `python scripts/fingerprint_scan.py /path/to/repo --format markdown` |
| Normalize terms                            | `references/taxonomy.md`                                             |
| Review evidence expectations               | `references/evidence_rules.md`                                       |
| Decide which runbooks to load next         | `references/deepening_guide.md`                                      |
| Surface attack / UQ / explainability hooks | `references/cross_cutting_concerns.md`                               |
| Start final report                         | `assets/fingerprint_report_template.md`                              |
| Check collection completeness              | `assets/evidence_checklist.md`                                       |

## Core Workflow

### 1. Inventory the repository

Use filesystem tools and, when helpful, `scripts/fingerprint_scan.py` to identify:
- README, docs, notebooks, papers, model cards
- dependency files and lockfiles
- training, evaluation, inference, and serving entrypoints
- config files
- prompts, retrieval assets, policies, simulators, datasets, tests

### 2. Produce a level-1 fingerprint

Using `references/taxonomy.md`, classify the repository along these dimensions:
- repository type
- task type
- input modality
- output modality
- model family
- framework
- training regime
- data characteristics
- serving pattern
- notable signals such as `multimodal`, `rag`, `safety-critical`, or `inference-only`

Every claim should include confidence and evidence, per `references/evidence_rules.md`.

### 3. Deepen selectively

Read `references/deepening_guide.md` and load only the runbooks that match the observed system. Common examples:
- `references/runbooks/vision.md`
- `references/runbooks/nlp_rag.md`
- `references/runbooks/tabular.md`
- `references/runbooks/timeseries.md`
- `references/runbooks/audio.md`
- `references/runbooks/retrieval_recsys.md`
- `references/runbooks/rl_control.md`
- `references/runbooks/multimodal.md`
- `references/runbooks/serving_security.md`

Do not force every repository through every runbook.

### 4. Annotate cross-cutting hooks

Use `references/cross_cutting_concerns.md` to note:
- likely attack surfaces
- likely uncertainty hooks
- likely explainability hooks
- governance or operational gaps

This step should annotate future work, not replace the dedicated skills.

### 5. Produce the fingerprint report

Use `assets/fingerprint_report_template.md`. A good report should include:
- repository summary
- normalized fingerprint
- relevant runbooks applied
- evidence-backed findings
- cross-cutting hooks
- unknowns
- recommended next analyses

## Evidence Discipline

- Prefer code, configs, tests, and executable artifacts over aspirational docs.
- If two sources conflict, report the conflict instead of guessing.
- If a claim is only weakly supported, lower confidence and state why.
- Multi-component systems may need multiple fingerprints or a top-level system fingerprint plus component notes.

## Output Expectations

Your output should be useful to another analyst or another skill. It should leave behind:
- a normalized taxonomy classification
- enough evidence for review
- a clear rationale for which deeper analyses matter next

## Integration with Downstream Analysis

The fingerprint informs deeper analysis capabilities:
- **Security testing**: use the fingerprint to choose attack classes and testing depth
- **Uncertainty analysis**: use the fingerprint to choose task-appropriate UQ methods
- **Explainability analysis**: use the fingerprint to choose model-appropriate explanation methods

## Common Pitfalls

**Don't classify based on repo name alone**: A repo called "sentiment-classifier" might actually be doing multi-task learning or have evolved into something else. Always validate against code and architecture.

**Don't over-index on config files**: Model configs can be stale, aspirational, or for experimentation only. Check which model actually loads in production/eval code.

**Don't miss hybrid architectures**: Systems can combine multiple model types (e.g., embedding model + classifier, retrieval + generation). Fingerprint the system, not just one component.

**Don't assign high confidence without finding the model**: If you can't locate model architecture code or loaded checkpoints, confidence should be medium or low. Inference-only repos with opaque APIs are especially tricky.
