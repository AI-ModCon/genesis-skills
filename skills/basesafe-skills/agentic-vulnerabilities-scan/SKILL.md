---
name: agentic-vulnerabilities-scan
description: Run an authorized, sandboxed Promptfoo red-team scan of a prompt-driven AI agent, chatbot, autonomous system, or tool-calling architecture when source access and a live target are available. Verify the target, isolate scan artifacts, obtain informed consent, then configure and execute only a bounded scan.
---

Use this workflow only for a target the user is authorized to test. Run it in a secure sandbox that is already configured with the target's approved environment variables. Do not use it to test third-party systems without authorization.

All generated artifacts are kept in `${AGENTIC_SCAN_DIR:-.agentic-vulnerabilities-scan}` beneath the target repository. Do not write scan artifacts to the repository root. The directory contains configuration, target findings, generated tests, provider wrappers, and results; treat it as sensitive.

## Preconditions and consent

Before probing the target or generating attacks, tell the user:

- the exact target and the proposed scan workspace;
- that the scan sends adversarial prompts to the target and may trigger real side effects;
- the configured Promptfoo host and that this skill always uses remote Promptfoo red-team generation;
- that target findings and any environment variables explicitly named in `AGENTIC_SCAN_PROVIDER_ENV` are written to the sensitive scan workspace;
- the selected plugins, strategies, test count, one-at-a-time concurrency, five-minute per-test timeout, and 30-minute total evaluation cap.

Ask for explicit confirmation before steps 4 and 5 unless the headless-policy procedure below succeeds. Offer a dry review of the configuration instead of execution. Remote Promptfoo red-team generation is required; abort if `PROMPTFOO_DISABLE_REDTEAM_REMOTE_GENERATION=true`.

## Headless policy

For headless execution, first establish and review the provider and configuration interactively. Then provide a read-only JSON policy through `AGENTIC_SCAN_POLICY` and set `AGENTIC_SCAN_HEADLESS=true`. The harness supplies target and Promptfoo hosts through controlled runtime environment variables; the policy approves plugin and strategy IDs and all scan limits. Remote generation remains required. Use `assets/headless-policy.example.json` as the schema and starting point; policies must never contain credentials or host configuration.

Run every phase with `python ${CLAUDE_SKILL_DIR}/scripts/run_scan_phase.py generate` or `evaluate` from the target repository. When `AGENTIC_SCAN_HEADLESS=true`, this runner automatically invokes the policy wrapper immediately before starting Promptfoo and fails closed when the environment or `promptfooconfig.yaml` exceeds the policy. Do not use a non-interactive harness flag as a substitute for this validation.

## Workflow

1. **Verify the target.** From the target repository, run `python ${CLAUDE_SKILL_DIR}/scripts/verify_target.py`. It resolves providers in this order: existing root `promptfooconfig.yaml`, root `provider.py`, OpenAI-compatible API, CLI, then a custom-provider template. It imports selected root files into the managed scan workspace. Abort if the target is unreachable or a provider cannot faithfully wrap the actual target.

2. **Fingerprint the target.** Inspect the source to understand the target's architecture, data, tools, and attack surface. Copy `${CLAUDE_SKILL_DIR}/assets/findings.md` to `${AGENTIC_SCAN_DIR:-.agentic-vulnerabilities-scan}/findings.md`, complete it, then run `python ${CLAUDE_SKILL_DIR}/scripts/report_findings_to_promptfoo.py` from the target repository.

3. **Bound the configuration.** Edit `${AGENTIC_SCAN_DIR:-.agentic-vulnerabilities-scan}/promptfooconfig.yaml`. Retain only relevant plugins and strategies. Interactive preflight defaults to two plugins, two strategies, two tests per plugin, and four total tests; override a limit only after the user explicitly approves the displayed scope by setting the corresponding `INTERACTIVE_SCAN_MAX_*` variable. The phase runner prints the effective bounds and blocks both generation and evaluation when any limit is exceeded.

4. **Generate attacks after consent or policy validation.** Obtain confirmation unless `AGENTIC_SCAN_HEADLESS=true`, then run `python ${CLAUDE_SKILL_DIR}/scripts/run_scan_phase.py generate` from the target repository. Monitor the command process directly; do not use sentinel files. Abort on errors.

5. **Evaluate after consent or policy validation.** Obtain confirmation unless `AGENTIC_SCAN_HEADLESS=true`, then run `python ${CLAUDE_SKILL_DIR}/scripts/run_scan_phase.py evaluate` from the target repository. Check initial output to confirm the target is responding and monitor the process. The runner treats failed red-team assertions as findings and returns zero after a completed evaluation; inspect `results.json` and report those failures. Abort on operational errors.

6. **Analyze and clean up.** Analyze `results.json` together with `findings.md`, report reproducible exploit evidence and mitigations, and tell the user where sensitive artifacts remain. On request, remove only the managed workspace with `python ${CLAUDE_SKILL_DIR}/scripts/cleanup_scan_workspace.py` from the target repository.

## Provider guidance

Custom Python and CLI providers execute the real target in the sandbox. Do not create a simulator. Only variables named in the comma-separated `AGENTIC_SCAN_PROVIDER_ENV` are copied into a persistent provider's configuration; ensure the list contains exactly the target variables the provider needs. Review the generated provider's target-specific import, response parsing, and concurrency behavior, then rerun verification until its smoke test passes.

## External resources

- [Promptfoo red-team configuration](https://www.promptfoo.dev/docs/red-team/configuration/)
- [Promptfoo red-team plugins](https://www.promptfoo.dev/docs/red-team/plugins/)
- [Promptfoo red-team strategies](https://www.promptfoo.dev/docs/red-team/strategies/)
