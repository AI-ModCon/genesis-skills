# Multimodal Runbook

Use this runbook when multiple modalities are first-class inputs or outputs.

## Inspect

- fusion architecture or orchestration layer
- modality-specific encoders
- alignment and synchronization code
- missing-modality handling
- evaluation broken down by modality combination

## Capture

- which modalities are primary vs auxiliary
- fusion strategy: early, late, cross-attention, retrieval-mediated
- whether components can fail independently
- serving path for combined inputs

## Common Hooks

- attack surface: cross-modal mismatch, poisoning, modality-drop failure
- uncertainty hooks: disagreement across modalities, fallback behavior
- explainability hooks: modality contribution and attribution

## Typical Unknowns

- behavior when one modality is absent or degraded
- which modality dominates the final decision

