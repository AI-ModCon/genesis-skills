# Retrieval and Recommendation Runbook

Use this runbook for ANN search, semantic retrieval, ranking, recommendation, or reranking pipelines.

## Inspect

- index construction and refresh logic
- embedding model and reranker definitions
- candidate generation and ranking code
- offline relevance metrics and online experimentation hooks
- serving API and feedback loops

## Capture

- whether the system is retrieval, ranking, recommendation, or all three
- corpus or candidate-source characteristics
- retrieval stack and indexing technology
- ranking metrics and evaluation method
- evidence of abstention or fallback on weak retrieval

## Common Hooks

- attack surface: index poisoning, manipulation of ranking signals, feedback loops
- uncertainty hooks: retrieval sufficiency, ranking confidence, abstention on sparse support
- explainability hooks: attribution of sources and score decomposition

## Typical Unknowns

- index freshness
- online metric governance
- manual curation or business-rule overlays

