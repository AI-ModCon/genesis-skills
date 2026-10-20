---
name: amsc-mag
description: Use this skill to work with the AmSC Model Access Gateway (MAG) at mag.genesis.americansciencecloud.org, the official OpenAI- and Anthropic-compatible LLM endpoint for American Science Cloud. Covers PAT authentication, model discovery and selection, model-string syntax (provider, effort, flex, compression), chat completions, embeddings, budget/429/401 troubleshooting, Claude Code setup (claude-amsc), and LangChain. Trigger on MAG, Model Access Gateway, AmSC LLM, AMSC_TOKEN, i2 API migration, or Claude Code with AmSC.
compatibility: Requires Python >= 3.10 (stdlib only) for the bundled scripts; network access to mag.genesis.americansciencecloud.org.
metadata:
  author: American Science Cloud Intelligent Interfaces Team
---

# AmSC Model Access Gateway (MAG)

Base URL: `https://mag.genesis.americansciencecloud.org` (Swagger/docs at the same URL).
OpenAI-compatible: `GET /v1/models`, `POST /v1/chat/completions`, `POST /v1/embeddings`.
Anthropic-compatible for Claude Code via `ANTHROPIC_BASE_URL`.

This replaces the deprecated legacy i2-api (see the `i2-api` skill for migration).

## Prerequisites

1. You need an approved Genesis Mission project with a MAG allocation.
2. Go to `https://my.amsc.energy.gov/dashboard` -> your project -> Personal Access Tokens -> Generate PAT.
3. The PAT is shown once and is short-lived. Export it for the current session, or keep it in a non-versioned secrets file you source on demand:

```bash
export AMSC_TOKEN=<your-pat>
```

4. When the PAT expires the MAG returns 401; generate a new one.

**Never hardcode or commit the token.** Scripts read it from `AMSC_TOKEN`, fail if unset, and never print it.

## Quick Start

```bash
python3 scripts/mag.py list-models
python3 scripts/mag.py chat --model claude-sonnet --message "Hello, world"
```

Scripts are stdlib-only.

## Model Strings

Format: `<base>[:<mod>]...[@<provider>]`

- Providers (company buckets): `openai`, `amazon` (Bedrock: Claude, Llama, Nova, gpt-oss, ...), `google` (Vertex Gemini), `microsoft` (Azure).
- Effort: `none|minimal|low|medium|high|xhigh|max`. Service tier: `flex`. Compression: `compact|compressed|nocompress`.
- `gpt-5.4:high:flex@openai` is identical to `gpt-5.4-high-flex@openai`. The dashed form exists for backward compatibility with CBorg clients; prefer the `:` syntax.
- A model's accepted modifiers are shown on the MAG Dashboard Models tab; an invalid one returns 400 `amsc_invalid_model_modifier`.
- Bare names (`claude-opus`, `claude-sonnet`, `claude-haiku`, `gemini-flash`) are aliases. They are mutable: the underlying model version can change without notice. Clients that require a specific version should use a model string with the version number. A bare name pins to one deployment per key for about an hour (not round-robin). Use `@provider` for a hard provider guarantee.
- Legacy hyphen suffixes and cborg path prefixes (`openai/`, `bedrock/`, `aws/`, `vertex_ai/`, `gemini/`, `azure/`) are accepted but not listed. `anthropic/` returns 404.
- Always query `GET /v1/models` for the live list. Do not hardcode model availability.

## Routing Headers

| Header | Value |
|---|---|
| `X-AmSC-MAG-Provider` | same as `@provider` (model string wins) |
| `X-AmSC-MAG-Effort` | effort level |
| `X-AmSC-MAG-Service-Tier` | `flex` or `standard` |
| `X-AmSC-MAG-Compression` | `compact`, `compressed`, `off` |

- An unusable header value is ignored (fail-soft). An unusable modifier in the model string is a 400 `amsc_invalid_model_modifier`.
- The response header `X-AmSC-MAG-Applied` states what was actually served (provider, effort, tier, compression). Read it to confirm. `mag.py chat` prints it to stderr.

```bash
python3 scripts/mag.py chat --model gpt-5.4 --provider openai \
  --effort high --service-tier flex --message "Summarize ..."
```

## Model Discovery and Selection

```bash
python3 scripts/mag.py list-models          # model ids
python3 scripts/mag.py list-models --json   # full metadata
```

To compare capabilities, prices and accepted modifiers, use the Models tab of the MAG Dashboard (https://mag.genesis.americansciencecloud.org/dashboard/).

## Chat and Embeddings

```bash
python3 scripts/mag.py chat --model claude-sonnet --system "Be concise." \
  --message "Explain quantum entanglement" --stream --max-retries 3
python3 scripts/mag.py embed --model <embedding-model-id> --input "Sample text"
```

Reasoning models spend reasoning tokens out of `max_completion_tokens`. Use at least about 2000 or the content may come back empty.

## Flex and Compression

- **Flex**: always 50% off, queued, 15-minute timeout; do not use on interactive paths. Availability is not guaranteed and a request may return 429, so the client must adapt (retry later or fall back to standard). Only some models support it (OpenAI-served GPT, Vertex Gemini flash). Bedrock has none.
- **Compression**: opt-in per request. `:compact` is the lossless profile; `:compressed` is aggressive. `compressed` preserves code blocks verbatim but drops low-information tokens in free-form prose, so do not use it when the model must edit or reproduce text verbatim (drafting a paper or documentation). Compression fails open, applies to chat only, and never to embeddings. Confirm what was applied in `X-AmSC-MAG-Applied`.

## Benchmarking and Reproducibility

Compression is off by default today, but the default may change. Clients that need exact fidelity or reproducible results (model benchmarks, regression suites, prompt comparisons) must not rely on the default:

- Disable compression explicitly: append `:nocompress` to the model string or send `X-AmSC-MAG-Compression: off`.
- Pin the model version with a versioned model string, not a bare alias (aliases are mutable).
- Pin the provider (`@provider`) so the same deployment family serves every run.
- Do not use flex for timed benchmarks; latency and availability vary.
- Record `X-AmSC-MAG-Applied` with each result to prove what was served.

```bash
python3 scripts/mag.py chat --model <versioned-model-id>:nocompress@<provider> --message "..."
```

## Limits and Errors

- Budgets are rolling per month, per-user and per-project, plus VO allocation limits. Monitor spend on the MAG dashboard.
- 429 has three causes: an exhausted budget window, per-user request-rate or concurrency limits (reduce parallel requests and back off), or provider throttling. Read the response body.
- 401 means an expired or invalid PAT: generate a new one.
- Limits: 120 requests per minute, no TPM cap, 5 parallel requests. Contact AmSC MAG support to request an increase.
- Timeouts: raise `--timeout` for long generations. Corporate TLS inspection: point `SSL_CERT_FILE` / `REQUESTS_CA_BUNDLE` (Python) or `NODE_EXTRA_CA_CERTS` (Node) at your CA bundle.

## Claude Code

Add the `claude-amsc` shell function from `references/claude-amsc.sh` to `~/.zshrc` or `~/.bashrc`:

```bash
source /path/to/amsc-mag/references/claude-amsc.sh
claude-amsc
```

The variables are set only for that invocation, so plain `claude` is unaffected. Do not set `ANTHROPIC_MODEL`, `ANTHROPIC_DEFAULT_*_MODEL`, or `CLAUDE_CODE_SUBAGENT_MODEL`; switch models with `/model`. For Haiku run `CLAUDE_CODE_AUTO_COMPACT_WINDOW=100000 claude-amsc` or `/autocompact 100000`. To pin a provider, run `MAG_PROVIDER=amazon claude-amsc` (opt-in; sends `X-AmSC-MAG-Provider`).

## LangChain / OpenAI SDK

```python
import os
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    model="claude-sonnet",
    base_url="https://mag.genesis.americansciencecloud.org/v1",
    api_key=os.environ["AMSC_TOKEN"],
    max_retries=3,
    timeout=600,
    default_headers={"X-AmSC-MAG-Provider": "amazon"},  # optional
)
print(llm.invoke("Explain quantum entanglement").content)
```

`OpenAIEmbeddings` takes the same `base_url` and `api_key`.
