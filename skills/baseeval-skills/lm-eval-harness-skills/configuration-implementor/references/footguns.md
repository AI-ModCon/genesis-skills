# Common Pitfalls and Troubleshooting Guide

This document highlights common pitfalls and troubleshooting tips when using this library. We'll continue to add more tips as we discover them.

## OpenAI-compatible API backend

### `openai-chat-completions`: base_url must be the full endpoint path

**Problem:** lm-eval's `openai-chat-completions` model posts directly to `self.base_url`
with no path appended. Passing a base URL such as `https://host/v1` returns 404.

```bash
# ❌ WRONG — results in 404 Not Found
--model_args "base_url=https://host/v1,model=..."

# ✅ RIGHT — includes the full completions path
--model_args "base_url=https://host/v1/chat/completions,model=..."
```

The default value in `OpenAIChatCompletion.__init__` is
`"https://api.openai.com/v1/chat/completions"`, confirming the expected form.

### `--apply_chat_template` required for chat endpoints

**Problem:** Without `--apply_chat_template`, lm-eval raises:
```
AssertionError: chat-completions require the --apply_chat_template flag.
```

Always pass `--apply_chat_template` when using `openai-chat-completions`.

```bash
lm_eval --model openai-chat-completions \
  --model_args "base_url=https://host/v1/chat/completions,model=<id>,api_key=<key>,system_instruction=<sys>" \
  --apply_chat_template \
  --tasks <task> --include_path <dir>
```

---

## `custom_dataset` function signature must include `**kwargs`

**Problem:** lm-eval passes extra keyword arguments (e.g. `version=`) to
`custom_dataset` functions. A signature without `**kwargs` raises `TypeError`
at dataset load time:

```
TypeError: load_my_fn() got an unexpected keyword argument 'version'
```

**Fix:** Always include `**kwargs` in every `custom_dataset` function:

```python
# ❌ WRONG — breaks when lm-eval passes extra kwargs
def load_my_fn(metadata=None, model_args=None):
    ...

# ✅ RIGHT — absorbs any extra keyword arguments
def load_my_fn(metadata=None, model_args=None, **kwargs):
    ...
```

---

## Whitespace-only stop sequences rejected by some endpoints

**Problem:** Some OpenAI-compatible endpoints (e.g. Bedrock-backed proxies)
reject newline characters as stop sequences with a 400 error such as
`stopSequences.0 is blank`.

This affects more than just explicit `until: ["\n"]` — the
`openai-chat-completions` model always sends at least one stop sequence and
defaults to `fewshot_delimiter="\n\n"` when `until` is absent. So omitting
`until` entirely does NOT avoid the problem.

**Fix:** Set `until` to a non-whitespace sentinel that the model will never
produce:

```yaml
generation_kwargs:
  until: ["###"]
```

Make sure your parser handles multi-line output gracefully (e.g. extract from
the first line only). A sentinel like `"###"` is safe because the model
won't emit it in a short letter-only response, and generation is bounded by
`max_gen_toks` anyway.

---

## `temperature: 0.0` rejected by some endpoints

**Problem:** Some endpoints (e.g. Bedrock-backed Claude with extended thinking
disabled) return a 400 error for `temperature=0.0`:

```
temperature may only be set to 1 when thinking is enabled
```

**Fix:** Make temperature configurable via an environment variable rather than
hardcoding `0.0` in the YAML. Use `${EVAL_TEMPERATURE:-1.0}` in the YAML (NEL
YAML env-var expansion syntax) or read it in any wrapper script.

```yaml
generation_kwargs:
  temperature: ${EVAL_TEMPERATURE:-1.0}
```

If the YAML format does not support env-var expansion, set it to `1.0` and
document the assumption. Never hardcode `0.0` without confirming the target
endpoint accepts it.

---

## YAML Configuration Issues

### Newline Characters in YAML (`\n`)

**Problem:** When specifying newline characters in YAML, they may be interpreted incorrectly depending on how you format them.

```yaml
# ❌ WRONG: Single quotes don't process escape sequences
generation_kwargs:
  until: ['\n']  # Gets parsed as the literal characters '\' and 'n' i.e "\\n"

```
```yaml
# ✅ RIGHT: Use double quotes for escape sequences
generation_kwargs:
  until: ["\n"]  # Gets parsed as an actual newline character

```

**Solutions:**
- Use double quotes for strings containing escape sequences
- For multiline content, use YAML's block scalars (`|` or `>`)
- When generating YAML programmatically, be careful with how template engines handle escape sequences

### Quoting in YAML

**When to use different types of quotes:**

- **No quotes**: Simple values (numbers, booleans, alphanumeric strings without special characters)
  ```yaml
  simple_value: plain text
  number: 42

  ```

- **Single quotes (')**:
  - Preserves literal values
  - Use when you need special characters to be treated literally
  - Escape single quotes by doubling them: `'It''s working'`
  ```yaml
  literal_string: 'The newline character \n is not processed here'
  path: 'C:\Users\name'  # Backslashes preserved

  ```

- **Double quotes (")**:
  - Processes escape sequences like `\n`, `\t`, etc.
  - Use for strings that need special characters interpreted
  - Escape double quotes with backslash: `"He said \"Hello\""`
  ```yaml
  processed_string: "First line\nSecond line"  # Creates actual newline
  unicode: "Copyright symbol: \u00A9"  # Unicode character

  ```
