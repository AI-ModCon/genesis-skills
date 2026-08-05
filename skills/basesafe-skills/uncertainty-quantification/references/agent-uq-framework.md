# Agent Uncertainty Quantification Framework

**Source**: [Uncertainty Quantification in LLM Agents: Foundations, Emerging Challenges, and Opportunities](https://arxiv.org/abs/2602.05073v2)  
**Authors**: Oh, Park, Kim, Li, Li, Yeh, Du, Hassani, Bogdan, Song, Li (2026)  
**Project Page**: https://agentuq.github.io/

## What Makes Agent UQ Different

Unlike single-turn LLM confidence, agent uncertainty must account for how confidence evolves across a trajectory. Two dynamics are fundamental:

- **Interactive actions** (tool calls, user queries): uncertainty can *decrease* as new information is gathered.
- **Non-interactive actions** (reasoning, writing to state): uncertainty *propagates* or increases.

Simple per-turn averaging misses this dynamic entirely. Agent UQ must also account for multiple sources of uncertainty: the agent's own model, external tools, user responses, and the environment.

## Choosing a Method

### By Agent Type

| Agent Type | Recommended Method(s) | Rationale |
|---|---|---|
| Tool-calling / RAG | Verbalized confidence + action classification | Low overhead; works with black-box APIs |
| Conversational | Verbalized confidence + information gating | Track whether user clarification reduces uncertainty |
| Planning / reasoning | Self-consistency variance | Captures branching uncertainty at decision points |
| Embodied / robotics | Verbalized confidence + world model | Separate model uncertainty from sensor/environment uncertainty |

### By Deployment Constraint

- **Low latency required**: Use verbalized confidence; avoid self-consistency sampling.
- **Batch processing**: Self-consistency or ensemble disagreement are affordable.
- **Access to output probabilities** (rare for frontier LLMs): Entropy or NLL are most theoretically grounded.

### Method Comparison

| Method | Access Required | Cost | Best For | Key Limitation |
|---|---|---|---|---|
| Verbalized Confidence | Black-box API | Negligible | Tool-use, conversational | Long contexts inflate confidence |
| Self-Consistency Variance | Black-box API | 3–5 extra generations | Planning, reasoning, code | Expensive for real-time |
| Action Classification | Agent logs | Moderate (extra LLM call) | All agents | Ambiguous edge cases |
| Information Gating | Logs + action classification | High | Conversational, trajectory-level | Requires mutual information estimate |
| World Model Approximation | Auxiliary LLM | High | Embodied, observation uncertainty | Approximation quality varies |
| Entropy / NLL | Output probabilities | Negligible | Research; proprietary models | Frontier LLMs restrict probability access |

**Start simple.** Deploy verbalized confidence first, validate with AUROC on ~50 trajectories, and add complexity only if that baseline is insufficient (AUROC < 0.60).

---

## Method Deep Dives

### Verbalized Confidence

Ask the LLM to score its own confidence after producing an answer, typically by appending a numeric rating instruction to the system prompt. The score is extracted from the final token(s) of the response.

**Empirical results** — cross-model comparison on tau-squared bench:

| Model | Domain | NLL AUROC | Entropy AUROC | Verbalized AUROC | Spearman |
|---|---|---|---|---|---|
| GPT-4.1 | Retail | 0.597 | 0.580 | 0.575 | 0.179 |
| GPT-4.1 | Telecom | 0.624 | 0.611 | 0.685 | 0.330 |
| Kimi-K2.5 | Retail | 0.469 | 0.468 | 0.523 | 0.039 |
| Kimi-K2.5 | Telecom | 0.645 | 0.664 | 0.580 | 0.051 |

Probability-based methods (NLL, Entropy) perform near-randomly. Verbalized confidence shows the strongest signal on GPT-4.1/Telecom but fails to reliably separate success and failure groups across the full trajectory.

**When to use**: Tool-calling or conversational agents; real-time systems.  
**When to avoid**: Safety-critical domains; when output probabilities are available.

---

### Self-Consistency Variance

Sample multiple outputs for the same prompt and measure disagreement via semantic similarity variance across the samples. High variance signals epistemic uncertainty. Works well for reasoning and code generation; less useful for deterministic tool calls.

**When to use**: Planning agents, code generation, batch workloads.  
**When to avoid**: Real-time systems; tool-calling agents.

---

### Action Classification

Classify each agent action along two axes using a secondary LLM call:

- **Interactivity**: interactive (asks questions, retrieves information) vs. non-interactive (thinks, writes to state, commits a final answer)
- **Evidentiality**: evidential (tool arguments and claims are traceable to user input or prior tool results) vs. non-evidential (contains hallucinated arguments, fabricated facts, or policy violations)

LLM classifiers achieve roughly 85–90% agreement with human annotators on conversational tasks. Evidentiality is particularly useful for detecting hallucination mid-trajectory, not just at the final output.

**When to use**: Anytime you need to track the *direction* of uncertainty change or model trajectory-level dynamics.  
**When to avoid**: Purely tool-using agents with no interactive steps.

---

### Information Gating

Weight each turn's uncertainty by whether the corresponding action increases or decreases information. The core idea:

- For **interactive actions**, uncertainty should decrease: the gating weight is negative, reflecting information gained relative to current uncertainty.
- For **non-interactive actions**, uncertainty propagates: the gating weight is positive, scaled by how much the observation depends on the committed action.

Trajectory-level uncertainty is the sum of these gated per-turn values. In practice, mutual information is expensive to compute exactly, so a heuristic is common: scale down the uncertainty score for interactive turns (information was gained) and leave it unchanged for non-interactive turns (uncertainty propagates). This enables detection of "stuck" states (uncertainty climbing over many turns) and supports escalation logic.

**When to use**: Conversational agents; trajectory-level uncertainty tracking.  
**When to avoid**: Simple point-estimate scenarios; when action classification is unavailable.

---

### World Model Approximation

Use an auxiliary LLM to predict what a tool or user will return, then score confidence in that prediction. High confidence in the predicted observation implies low observation uncertainty; low confidence implies high uncertainty. Auxiliary LLM predictions match ground truth roughly 70% of the time; accuracy is higher for stochastic domains (user responses) than deterministic tool calls.

**When to use**: Embodied agents; multi-turn tasks with diverse observation sources.  
**When to avoid**: Deterministic tool-calling agents.

---

### Hybrid Approaches

For embodied agents, combine verbalized confidence (agent's own uncertainty) with a world model estimate (observation uncertainty), weighting each by their relative contribution. For conversational agents, accumulate gated uncertainty turn-by-turn using action classification. For planning agents, combine self-consistency variance over proposed steps with verbalized confidence at commitment points, and trigger replanning if either exceeds a threshold.

---

## Validation

### If you have trajectory-level labels

- **AUROC**: Does uncertainty predict failure? Target > 0.65 for a useful signal.
- **Spearman correlation**: Between uncertainty and task success. Target > 0.3 for moderate signal.
- **Risk-coverage curve**: Does high confidence correspond to high success rate?

| AUROC | Interpretation | Next Step |
|---|---|---|
| < 0.55 | No signal | Debug labels; try a different prompt or method |
| 0.55–0.65 | Weak signal | Add action classification or information gating |
| 0.65–0.75 | Moderate; usable | Deploy with threshold validation; monitor |
| > 0.75 | Strong | Good baseline; consider complementary methods |

### If you lack trajectory labels

- **Milestone-based evaluation**: Label key decision points only.
- **Human spot-checks**: Annotate a random sample.
- **Proxy metrics**: Task success rate as a weak signal.

Note: a survey of 44 agent benchmarks found that 68% provide only trajectory-level (final outcome) labels, 24% provide milestone-level labels, and just 9% annotate every turn. Turn-level ground truth is rare, making validation of uncertainty *dynamics* difficult in practice.

---

## Common Mistakes

**Aggregating without action conditioning**  
Plain averaging treats all turns equally. Non-interactive reasoning accumulates uncertainty while interactive clarification reduces it. Averaging hides this dynamic. Fix: use action classification and information gating.

**Ignoring observation uncertainty**  
Estimating only action uncertainty and assuming tool or user responses are deterministic breaks the decomposition when those sources are noisy. Fix: model observation uncertainty with an auxiliary LLM or domain-specific datastore.

**No operational decision policy**  
Reporting a single uncertainty number without attached thresholds or responses changes nothing. Fix: define explicit thresholds—proceed, monitor, escalate, or rollback.

**Trajectory-only evaluation**  
Two failing trajectories can have very different uncertainty profiles. Final success/failure alone masks intermediate patterns. Fix: evaluate at milestones or collect sparse turn-level labels.

**Over-engineering before validating the baseline**  
Jumping to information gating and world models without testing verbalized confidence first adds cost and complexity with no debugging baseline. Fix: start with verbalized confidence; add complexity only if AUROC < 0.60.

---

## Practical Applications

**Healthcare**: Track trajectory uncertainty during clinical decision support. Route low-uncertainty steps autonomously (history collection, standard tests); surface accumulated uncertainty to clinicians before final diagnosis.

**Software Engineering**: Monitor uncertainty over patch candidates. Trigger exploration, user clarification, or rollback when confidence falls below threshold—mirroring a human engineer's practice of gathering evidence before committing to a fix.

**Robotics**: Distinguish epistemic uncertainty (agent doesn't know what to do) from aleatoric uncertainty (sensor noise). High epistemic uncertainty → explore or request clarification. High aleatoric uncertainty → request re-sensing or defer action.

---

## When NOT to Use Agent UQ

| Scenario | Alternative |
|---|---|
| Agent produces single-turn outputs only | Standard LLM UQ (entropy, calibration) |
| Success is deterministic given inputs | Rule-based verification or checklists |
| Uncertainty signals won't affect deployment | Build a decision policy first |
| Very low-stakes domain | Simple confidence thresholds |
| Frontier LLM with restricted probability access | Proxy metrics (retrieval scores, execution time) |

---

## Related Research

- **Single-turn LLM UQ**: Kadavath et al. (2022), Lin et al. (2022), Manakul et al. (2023), Farquhar et al. (2024), Aichberger et al. (2024)
- **Multi-turn reasoning**: Fu et al. (2025), Wang et al. (2023), Lightman et al. (2024)
- **Agent-specific**: Oh et al. (2026), Chan et al. (2025), Zhao et al. (2025)
- **Multi-agent UQ**: Tang et al. (2026), Yoffe et al. (2025), Feng et al. (2025)
- **Benchmarks**: tau-squared bench (Barres et al., 2025), AgentBench (Liu et al., 2024), ToolSandbox (Lu et al., 2025)

## Open Problems

**Aleatoric vs. epistemic ambiguity in agents**: In single-turn QA, the correct answer is typically unique. In agentic tasks, intermediate steps may be intrinsically ambiguous — multiple valid tool sequences can reach the same goal. Current UQ methods cannot distinguish agent ignorance (epistemic) from genuine task multiplicity (aleatoric).

**Multi-agent UQ**: This framework addresses single-agent environments. Multi-agent systems introduce inter-agent communication uncertainty, debate collapse risk, and collective uncertainty dynamics that have no established UQ treatment.

**Self-improving agents**: Agents that adapt across episodes using uncertainty for continual learning have non-stationary uncertainty dynamics (context memory and model parameters evolve), requiring modeling approaches that do not yet exist.

**Primary source**: Oh et al. (2026) — [Uncertainty Quantification in LLM Agents: Foundations, Emerging Challenges, and Opportunities](https://arxiv.org/abs/2602.05073v2)
