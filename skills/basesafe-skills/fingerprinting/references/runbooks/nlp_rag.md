# NLP and RAG Runbook

Use this runbook for text generation, summarization, QA, chat systems, retrieval-augmented generation, or agentic text workflows.

## Inspect

- prompts, templates, and system instructions
- tokenizer and embedding stack
- retriever, vector store, reranker, and citation logic
- evaluation prompts and answer-quality metrics
- tool integration and agent planning code

## Capture

- primary task: generation, summarization, retrieval, QA, agent orchestration
- model family and provider stack
- whether retrieval is mandatory, optional, or absent
- serving pattern and human review path
- evidence of refusal, grounding, or escalation policy

## Common Hooks

- attack surface: prompt injection, context poisoning, retrieval poisoning, tool abuse
- uncertainty hooks: self-consistency, answerability, retrieval sufficiency, refusal thresholds
- explainability hooks: citations, source attribution, traceable tool use

## Typical Unknowns

- prompt versions actually deployed
- retriever refresh cadence
- production evaluation distribution
- hidden middleware or provider policies

