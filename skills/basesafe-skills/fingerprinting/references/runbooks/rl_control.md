# RL and Control Runbook

Use this runbook for reinforcement learning, control systems, or simulator-dependent decision policies.

## Inspect

- environment or simulator definitions
- reward functions and safety constraints
- rollout generation and replay buffers
- evaluation scenarios and termination conditions
- deployment interfaces for actions or control outputs

## Capture

- whether the system is simulation, control, or offline RL
- environment assumptions and observability
- policy and value-network families
- training regime and evaluation loop
- safety and fallback controls

## Common Hooks

- attack surface: reward hacking, simulator mismatch, spoofed observations
- uncertainty hooks: state uncertainty, policy instability, safe fallback thresholds
- explainability hooks: policy traces, scenario analysis, reward contribution review

## Typical Unknowns

- production environment mismatch from training simulator
- safety envelope under rare states
- human override process

