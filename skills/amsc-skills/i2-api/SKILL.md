---
name: i2-api
description: DEPRECATED. The legacy AmSC i2-api (api.i2-core.american-science-cloud.org) is retired in favor of the Model Access Gateway (MAG). Use this skill only to migrate an existing i2-api setup; for all LLM work use the amsc-mag skill. Trigger on i2 API, i2-core, AMSC_I2_API_KEY, or API Key Manager.
metadata:
  author: American Science Cloud Intelligent Interfaces Team
---

# i2-api (deprecated)

The legacy i2-api is deprecated. Do not use it for new work, and do not generate code that targets it. Existing i2-api users must migrate to the AmSC Model Access Gateway (MAG). Use the `amsc-mag` skill for everything LLM-related.

## Old to new

| | Legacy i2-api | MAG |
|---|---|---|
| Host | `api.i2-core.american-science-cloud.org` | `https://mag.genesis.americansciencecloud.org` |
| Login | AmSC Google login | Ping Identity (AmSC IdP) |
| Credential | API key from "API Key Manager" | Personal Access Token (PAT) |
| Env var | `AMSC_I2_API_KEY` | `AMSC_TOKEN` |
| Where to create | i2-api web UI | `https://my.amsc.energy.gov/dashboard` -> project -> Personal Access Tokens -> Generate PAT |
| Requirement | any key | approved project with a MAG allocation |

Migration steps:

1. Generate a PAT (short-lived; a 401 means generate a new one) and export `AMSC_TOKEN`.
2. Replace the base URL with `https://mag.genesis.americansciencecloud.org/v1`.
3. Replace `AMSC_I2_API_KEY` with `AMSC_TOKEN` in code and shell config.
4. Re-check model names against `GET /v1/models`; the MAG uses `<base>[:<mod>]...[@<provider>]` model strings.
5. For Claude Code, replace the old exported environment with the scoped `claude-amsc` function in `amsc-mag/references/claude-amsc.sh`.

See the `amsc-mag` skill for details.
