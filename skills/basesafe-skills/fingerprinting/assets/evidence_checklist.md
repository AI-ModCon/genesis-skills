# Fingerprinting Evidence Checklist

Use this checklist before finalizing a repository fingerprint.

## Repository Basics

- [ ] Top-level purpose identified
- [ ] Primary languages identified
- [ ] Dependency files reviewed
- [ ] Likely entrypoints identified

## Model Classification

- [ ] Task type classified
- [ ] Input modality classified
- [ ] Output modality classified
- [ ] Model family or pipeline type classified
- [ ] Framework or stack identified

## Training / Evaluation

- [ ] Training regime identified or marked unknown
- [ ] Evaluation artifacts reviewed
- [ ] Important configs reviewed
- [ ] Key unknowns documented

## Serving / Operations

- [ ] Serving pattern identified or marked absent
- [ ] External interfaces identified
- [ ] Monitoring or fallback signals noted if present

## Cross-Cutting Hooks

- [ ] Attack-surface hooks noted
- [ ] UQ hooks noted
- [ ] Explainability hooks noted

## Evidence Quality

- [ ] Strong claims have direct evidence
- [ ] README-only claims are marked conservatively
- [ ] Conflicts are surfaced explicitly
- [ ] Confidence is stated honestly

