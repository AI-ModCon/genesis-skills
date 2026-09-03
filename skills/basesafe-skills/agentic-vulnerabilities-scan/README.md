# Agentic Vulnerabilities Scan

This skill performs a Promptfoo-based red-team scan of a prompt-driven AI system.
It verifies a live target, uses source code to tailor the scan, generates adversarial prompts, evaluates the actual target, and reports actionable findings.

Use it only when you have access to the target's source code, a live or executable prompt interface, and authorization to test the target.

Use of promptfoo requires API keys. See [credentials and environment variables](#credentials-and-environment-variables).

## How it works

The skill:

1. Verifies the approved Promptfoo host and the live target, then prepares an isolated scan workspace.
2. Fingerprints the target source code, recording its architecture and attack surface in `findings.md`.
3. Integrates those findings into Promptfoo's red-team configuration in `promptfooconfig.yaml`.
4. Edits the config to select relevant Promptfoo plugins and strategies, keeping the first run small.
5. Executes `promptfoo redteam generate` in the scan workspace to generate redteam evals (`redteam.yaml`).
6. Executes the tests with one-at-a-time concurrency, a five-minute per-test timeout, and a 30-minute evaluation cap.
7. Reviews and reports actionable findings.

## Requirements

The skill itself depends on Python 3 (+ the `ruyaml` package), and the Promptfoo client (installed via Node.js as in `npm install -g promptfoo`).

### Credentials and environment variables

Never place API keys in this skill directory or commit them to source control. Copy [`.example.env`](.example.env) outside the skill directory, populate the required values, and uncomment only the settings for the provider mode you use. Optional variables are deliberately commented out because an empty assignment can select an invalid provider or workspace.

**Required**
Set non-empty `PROMPTFOO_HOST` and `PROMPTFOO_API_KEY` for the exact Promptfoo host approved for the scan.

**Target-Specific Environment Variables**
- For a target that is OpenAI-compatible, set `MODEL_ENDPOINT` and `MODEL`; set `MODEL_AUTH_TOKEN` only if the endpoint requires bearer authentication.
- For a target that is accessed via CLI subprocess, set `MODEL_COMMAND` with a `{PROMPT}` placeholder.
- For a target that is imported via python or accessed via CLI subprocess, set `AGENTIC_SCAN_PROVIDER_ENV`.

`AGENTIC_SCAN_PROVIDER_ENV` is a whitelist of environment variables that are passed to the target.
Its value is a comma-separated list of variable *names*, not values. Each named variable must already exist in the current sandbox environment.
Do not list unrelated sandbox variables, as every listed value becomes part of the sensitive scan workspace configuration.

Promptfoo subprocesses receive a separate fixed allowlist containing only its
runtime/configuration directories, Promptfoo authentication and generation
settings, and the OpenAI-compatible provider settings. Unrelated ambient
environment variables are not passed to Promptfoo.

**Optional scan settings**

- Set `AGENTIC_SCAN_DIR` only to a dedicated subdirectory of the target repository; otherwise the default is `.agentic-vulnerabilities-scan`.
- Interactive preflight defaults to two plugins, two strategies, two tests per plugin, and four total tests. To raise a limit after explicit approval, set the corresponding `INTERACTIVE_SCAN_MAX_PLUGINS`, `INTERACTIVE_SCAN_MAX_STRATEGIES`, `INTERACTIVE_SCAN_MAX_TESTS_PER_PLUGIN`, or `INTERACTIVE_SCAN_MAX_TOTAL_TESTS` variable.
- For a policy-controlled headless scan, set `AGENTIC_SCAN_HEADLESS=true` and `AGENTIC_SCAN_POLICY` to an approved read-only policy file. Do this only after an interactive scan has established the target integration.

### Runtime and Sandboxing

Run the agentic harness that executes skill (e.g., the skill was developed for Claude Code) in a secure sandbox that can access the target (e.g., over the network, via OpenAI-compatible API) or execute it (e.g., from source, with included dependencies and environment variables).

The sandbox should enforce the intended filesystem, network, credential, and privilege boundaries; the skill does not create those boundaries itself.

### Scan workspace

All artifacts are written to `${AGENTIC_SCAN_DIR:-.agentic-vulnerabilities-scan}` within the target repository. `AGENTIC_SCAN_DIR` must name a dedicated subdirectory, never the repository root:

- `promptfooconfig.yaml`
- `redteam.yaml`
- `provider.py`
- `findings.md`
- `results.json`

The skill reuses the dedicated workspace directory when it already exists so that successive runs can be built upon.
On request, remove a completed workspace with `python ${CLAUDE_SKILL_DIR}/scripts/cleanup_scan_workspace.py` from the target repository.

## Configuration of target

Promptfoo accesses the target via a **provider**.

This skill attempts to detect or configure, in order:
1. A provider specified by an existing `promptfooconfig.yaml` file in the working directory. The skill imports that configuration into the scan workspace without changing the source file.
2. An existing `provider.py` file in the working directory. The skill copies it into the scan workspace and configures promptfoo to use it.
3. An OpenAI-compatible API endpoint, specified by environment variables.
4. A stdio/CLI interface, specified by environment variables.
5. Some other way of driving the target via Python.
   - The skill will attempt to construct one via inspection of the target's source code.

### Example: OpenAI-compatible HTTP target

Set `MODEL_ENDPOINT` to the exact HTTP endpoint that accepts the OpenAI-style chat-completions `POST` request used by the target.
`MODEL` must identify a model that both Promptfoo and the target accept.
Set `MODEL_AUTH_TOKEN` only when the endpoint requires bearer authentication.

```sh
export MODEL_ENDPOINT=https://staging-api.example.com/v1/chat/completions
export MODEL=openai:chat:aquarius-10.0
export MODEL_AUTH_TOKEN="my-api-key"
```

This skill will use these values to configure the appropriate provider for Promptfoo.

### Example: CLI Subprocess Target

`MODEL_COMMAND` is parsed as a command line, not run through a shell. It must contain a `{PROMPT}` placeholder, and runs with the target repository as its working directory.

```sh
export MODEL_COMMAND='stdio-target-frontend --prompt "{PROMPT}"'
export EXAMPLE_ENV_VAR_NEEDED_BY_TARGET="my-config"
export AGENTIC_SCAN_PROVIDER_ENV=MODEL_COMMAND,EXAMPLE_ENV_VAR_NEEDED_BY_TARGET
```

This skill will use these values to configure the appropriate provider for Promptfoo.

**CLI prompt contract**

Promptfoo supplies the custom provider's `prompt` argument as either a plain final prompt string or a JSON-encoded OpenAI-style message array. The message form is an ordered list of objects with string `role` and `content` fields:

```json
[
  {"role": "system", "content": "You are a concise assistant."},
  {"role": "user", "content": "Summarize this document."},
  {"role": "assistant", "content": "Please provide the document."},
  {"role": "user", "content": "Here it is: ..."}
]
```

- A CLI target that supports multi-turn conversations must accept such a PROMPT value, parse it as JSON, and use the ordered messages as the complete history.
- A CLI target that does not support multi-turn conversations can treat a non-JSON argument as the user prompt, but should reject or explicitly flatten a JSON-valued message array rather than silently misinterpreting it.

For example, a Python CLI can normalize its prompt argument as follows:

```python
import json

def messages_from_argument(value: str) -> list[dict[str, str]]:
    try:
        messages = json.loads(value)
    except json.JSONDecodeError:
        return [{"role": "user", "content": value}]
    if not isinstance(messages, list) or not all(
        isinstance(message, dict)
        and isinstance(message.get("role"), str)
        and isinstance(message.get("content"), str)
        for message in messages
    ):
        raise ValueError("Expected a prompt string or a JSON message array")
    return messages
```

This is stateless replay: each CLI invocation receives the complete history; it does not itself create a persistent target-side session.

### Example: Custom `provider.py`

This skill looks for a user-supplied `provider.py` before checking for a supplied OpenAI-compatible API endpoint or CLI command. Failing these checks, it finally attempts to create a `provider.py` from source-code inspection of the target, with supplied templates at `assets/provider_*.py`.
Python providers are [documented by promptfoo](https://www.promptfoo.dev/docs/providers/python/).

All information necessary to configure the target, including required environment variables, must be available at runtime.

```sh
export EXAMPLE_ENV_VAR_NEEDED_BY_TARGET="my-config"
export AGENTIC_SCAN_PROVIDER_ENV=EXAMPLE_ENV_VAR_NEEDED_BY_TARGET
```

## Running a scan: interactive or headless

This skill can run interactively (recommended for the first run) or autonomously in CI/CD or a periodic test suite.

### Interactive mode (default)

Use interactive mode for the initial scan.
After target verification and configuration, the invoking agent must obtain explicit confirmation before test generation and again before evaluation.
Before each interactive phase, the standard phase runner prints the configured plugin, strategy, and plugin-test counts together with the effective `INTERACTIVE_SCAN_MAX_*` limits. It blocks generation and evaluation when the configuration exceeds a limit. The defaults are two plugins, two strategies, two tests per plugin, and four total tests.
During evaluation, failed red-team assertions are expected findings rather than runner errors. The phase runner records them in `results.json` and exits successfully after a completed evaluation; operational failures still return a nonzero status.
We recommend reviewing and retaining successful workspace artifacts for future headless runs.

### Headless mode

After an initial interactive run has established a successful testing pipeline for the target, a harness may run later scans without user interaction. To do so, set `AGENTIC_SCAN_HEADLESS=true` and provide a read-only JSON policy by setting its path as `AGENTIC_SCAN_POLICY`. The standard phase runner detects that setting and validates the policy automatically. A generic harness setting such as `--dangerous-no-interaction` does not replace this policy check.

The policy contains no credentials or host configuration. The harness supplies `MODEL_ENDPOINT` and `PROMPTFOO_HOST` as controlled runtime environment variables. The policy approves plugin and strategy IDs and hard limits for test count, concurrency, and timeouts. Start with [`assets/headless-policy.example.json`](assets/headless-policy.example.json); keep the deployed policy outside the target repository or mount it read-only.

Example policy for a small staging scan:

```json
{
  "version": 1,
  "headless": true,
  "scan": {
    "allowed_plugins": ["prompt-extraction", "hijacking"],
    "allowed_strategies": ["jailbreak:meta", "jailbreak:hydra"],
    "max_plugins": 2,
    "max_strategies": 2,
    "max_tests_per_plugin": 2,
    "max_total_tests": 4,
    "max_concurrency": 1,
    "max_test_timeout_ms": 300000,
    "max_eval_time_ms": 1800000
  }
}
```


```sh
export AGENTIC_SCAN_HEADLESS=true
export AGENTIC_SCAN_POLICY=/path/to/policy.json
export PROMPTFOO_HOST=https://promptfoo.internal.example
```

Configure these values in the harness environment. The harness invokes the skill's normal phase runner: it detects `AGENTIC_SCAN_HEADLESS=true` and validates the policy before invoking Promptfoo; otherwise the agent obtains interactive confirmation before each phase. No manual script invocation is required.

## Outputs

The local scan workspace contains the reproducible artifacts: `findings.md`, `promptfooconfig.yaml`, `provider.py` when used, generated `redteam.yaml`, and `results.json`. Treat this workspace as sensitive because it can contain target architecture details, approved provider configuration, adversarial prompts, and results.


### Reporting

Promptfoo provides a UI for viewing the results via `promptfoo view .` and a command for reporting on the redteam findings `promptfoo redteam report`, both of which should be executed from the artifacts directory (`.agentic-vulnerabilities-scan`)

The results of the evaluation can be logged to the connected promptfoo server with `promptfoo share`. 
This command is not executed by default. 
