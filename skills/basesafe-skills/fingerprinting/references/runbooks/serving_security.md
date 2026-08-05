# Serving and Security Runbook

Use this runbook when deployment architecture materially shapes system behavior or risk.

## Inspect

- API servers, workers, gateways, and background jobs
- container, orchestration, and deployment manifests
- auth, rate limiting, validation, and logging paths
- monitoring, drift detection, and rollback logic
- model artifact loading and version management

## Capture

- serving pattern: batch, API, webapp, edge, mobile, human-in-the-loop
- operational dependencies
- versioning and rollback strategy
- observability and alerting
- exposed interfaces and trust boundaries

## Common Hooks

- attack surface: input abuse, auth gaps, logging leaks, model extraction
- uncertainty hooks: production monitoring and fallback policies
- explainability hooks: audit logs, traceability, user-facing rationale paths

## Typical Unknowns

- production-only middleware
- hidden infrastructure controls
- incident response workflow

