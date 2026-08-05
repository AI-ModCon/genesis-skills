---
name: i2-api
description: Use this skill to work with the AmSC i2 LLM API at api.i2-core.american-science-cloud.org, including API key validation, model discovery and selection, chat completions, embeddings, cost/spend tracking, Claude Code configuration, and LangChain integration. Trigger this skill when the task mentions i2 API, AmSC LLM, model selection, chat completions, embeddings, API spend, Claude Code setup with i2, or LangChain with i2.
compatibility: Requires Python >= 3.10 and the requests package (used by scripts/key_manager.py and scripts/i2_api_call.py)
metadata:
  author: American Science Cloud Intelligent Interfaces Team
---

# AmSC i2 API

Use scripted workflows. Prefer the bundled scripts over hand-written `curl` commands.

## Prerequisites

1. Go to `https://api.i2-core.american-science-cloud.org/`
2. Log in with your AmSC Google credentials
3. Click "API Key Manager" in the upper right corner
4. Generate a key
5. Set the environment variable:

```bash
export AMSC_I2_API_KEY=<your-key>
```

6. Ensure Python >= 3.10 with the `requests` package installed:

```bash
python3 -m pip install requests
```

**IMPORTANT**: Never hardcode API keys in source code. Always use environment variables.

## Quick Start

1. Validate your key:
```bash
python3 scripts/key_manager.py status
```

2. List available models:
```bash
python3 scripts/i2_api_call.py list-models
```

3. Send a chat message:
```bash
python3 scripts/i2_api_call.py chat --model claude-sonnet --message "Hello, world"
```

## Key Management

Use `scripts/key_manager.py` for key validation and spend tracking.

- Check if key is set and valid:
```bash
python3 scripts/key_manager.py status
```

- Check budget and current spend:
```bash
python3 scripts/key_manager.py spend
```

- Machine-readable output:
```bash
python3 scripts/key_manager.py status --json
python3 scripts/key_manager.py spend --json
```

Notes:
- Key is read from `AMSC_I2_API_KEY` environment variable
- Allow up to 5 seconds after an API call for spend logs to update

## Model Discovery and Selection

### Inspect Available Models

- List all model IDs grouped by mode:
```bash
python3 scripts/i2_api_call.py list-models
```

- Get detailed metadata for all models:
```bash
python3 scripts/i2_api_call.py model-info
```

- Get metadata for a specific model:
```bash
python3 scripts/i2_api_call.py model-info --model claude-sonnet
```

- Extract a specific property across all models:
```bash
python3 scripts/i2_api_call.py model-info --property supports_prompt_caching
```

### Select the Best Model

Use `scripts/select_model.py` to find the optimal model for your requirements.

**CLI filter mode** -- specify requirements as flags:
```bash
python3 scripts/select_model.py \
  --mode chat \
  --vision required \
  --reasoning high \
  --tools required \
  --min-context 100000 \
  --caching preferred \
  --optimize cost
```

**Natural language mode** -- describe requirements as text:
```bash
python3 scripts/select_model.py \
  --describe "I need a model for coding tasks with function calling, \
  at least 128K context, and prompt caching. Cost is important."
```

**Interactive interview mode** -- answer prompts:
```bash
python3 scripts/select_model.py --interview
```

Available filter flags:

| Flag | Values | Description |
|------|--------|-------------|
| `--mode` | `chat`, `embedding` | Model type |
| `--vision` | `required`, `preferred`, `not-needed` | Image input support |
| `--reasoning` | `high`, `standard`, `not-needed` | Extended reasoning mode |
| `--tools` | `required`, `preferred`, `not-needed` | Function/tool calling |
| `--min-context` | integer | Minimum context window (tokens) |
| `--min-output` | integer | Minimum max output (tokens) |
| `--caching` | `required`, `preferred`, `not-needed` | Prompt caching support |
| `--json-mode` | `required`, `preferred`, `not-needed` | JSON output mode |
| `--optimize` | `cost`, `capability`, `balanced` | Optimization target |
| `--top` | integer | Number of results to show (default: 3) |
| `--json` | flag | Machine-readable output |

## Chat Completions

Basic chat call:
```bash
python3 scripts/i2_api_call.py chat \
  --model claude-sonnet \
  --message "Explain quantum entanglement in one paragraph"
```

With a system prompt:
```bash
python3 scripts/i2_api_call.py chat \
  --model claude-sonnet \
  --system "You are a concise technical writer." \
  --message "Explain quantum entanglement"
```

Streaming response:
```bash
python3 scripts/i2_api_call.py chat \
  --model claude-sonnet \
  --message "Write a short story" \
  --stream
```

With token limit:
```bash
python3 scripts/i2_api_call.py chat \
  --model claude-haiku \
  --message "Summarize this text" \
  --max-tokens 256
```

With retry on transient failures:
```bash
python3 scripts/i2_api_call.py chat \
  --model claude-sonnet \
  --message "Hello" \
  --max-retries 3
```

## Embeddings

Generate an embedding:
```bash
python3 scripts/i2_api_call.py embed \
  --model cohere-embed-english-v3 \
  --input "The quick brown fox jumps over the lazy dog"
```

Raw JSON output:
```bash
python3 scripts/i2_api_call.py embed \
  --model cohere-embed-v4 \
  --input "Sample text" \
  --json
```

## Cost Management

Estimate cost before a call:
```bash
python3 scripts/i2_api_call.py cost-estimate \
  --model claude-sonnet \
  --input-tokens 1000 \
  --output-tokens 500
```

Check current spend:
```bash
python3 scripts/key_manager.py spend
```

Notes:
- After a call, the true cost is in the `x-litellm-response-cost` response header
- Use `--json` with `i2_api_call.py` subcommands to see full response headers
- Use smaller/cheaper models (haiku, gpt-oss-20b) for routine tasks; escalate to larger models only when needed

## Claude Code Setup

Source the env var template to configure Claude Code with i2 as the backend:

```bash
source references/claude-code-env.sh
```

Or add the contents of `references/claude-code-env.sh` to your shell profile (`~/.zshrc` or `~/.bashrc`).

After sourcing, verify the variables are set:
```bash
env | grep ANTHROPIC
```

Then start Claude Code normally:
```bash
cd my-project
claude
```

See `references/claude-code-env.sh` for all configurable variables and their descriptions.

## LangChain Integration

The i2 API is OpenAI-compatible. Use `langchain-openai` with the i2 base URL.

### Chat Model

```python
import os
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    model="claude-sonnet",
    base_url="https://api.i2-core.american-science-cloud.org/v1",
    api_key=os.environ["AMSC_I2_API_KEY"],
)

response = llm.invoke("Explain quantum entanglement")
print(response.content)
```

### Embeddings

```python
import os
from langchain_openai import OpenAIEmbeddings

embeddings = OpenAIEmbeddings(
    model="cohere-embed-english-v3",
    base_url="https://api.i2-core.american-science-cloud.org/v1",
    api_key=os.environ["AMSC_I2_API_KEY"],
)

vector = embeddings.embed_query("Sample text")
```

### Streaming

```python
import os
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    model="claude-sonnet",
    base_url="https://api.i2-core.american-science-cloud.org/v1",
    api_key=os.environ["AMSC_I2_API_KEY"],
    streaming=True,
)

for chunk in llm.stream("Write a short story"):
    print(chunk.content, end="", flush=True)
```

### Retry Handling

Always wrap inference calls in retry logic for production use:

```python
import os
import time
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    model="claude-sonnet",
    base_url="https://api.i2-core.american-science-cloud.org/v1",
    api_key=os.environ["AMSC_I2_API_KEY"],
    max_retries=3,
    timeout=600,
)
```

## Network Issues

### SSL Certificate Errors

If you use Netskope or similar VPN software, register the CA certificate bundle:

```bash
# Python
export REQUESTS_CA_BUNDLE=/path/to/ca-cert.pem
export SSL_CERT_FILE=/path/to/ca-cert.pem

# Node.js
export NODE_EXTRA_CA_CERTS=/path/to/ca-cert.pem
```

Contact your IT support to obtain the CA certificate bundle.

### Timeout Errors

Use `--timeout` to increase the request timeout:
```bash
python3 scripts/i2_api_call.py chat \
  --model claude-opus \
  --message "Write a detailed analysis" \
  --timeout 600
```

### Transient Network Errors

Use `--max-retries` for automatic retry with exponential backoff:
```bash
python3 scripts/i2_api_call.py chat \
  --model claude-sonnet \
  --message "Hello" \
  --max-retries 5
```

Retry sleep follows `min(1 * 2^attempt, 30)` seconds between attempts.
