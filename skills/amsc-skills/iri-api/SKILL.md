---
name: iri-api
description: Use this skill to work with IRI API deployments at NERSC (https://api.iri.nersc.gov) and ALCF (https://api.alcf.anl.gov) via reproducible scripts, including Globus token lifecycle management (status, refresh, interactive login) and OpenAPI-driven endpoint execution for facility/status/account/compute/filesystem/task workflows. Trigger this skill when the task mentions IRI API, openapi.json-driven calls, authenticated endpoint access, job submission/status/cancel, file operations, task polling/cleanup, or running jobs on Perlmutter or Polaris.
metadata:
  author: American Science Cloud Intelligent Interfaces Team
---

# IRI API

Use scripted workflows. Prefer the bundled scripts over hand-written `curl` commands.

## Deployments

| Site | Base URL | Auth script | Reference |
|---|---|---|---|
| NERSC (Perlmutter) | `https://api.iri.nersc.gov` (default) | `scripts/token_manager.py ensure --facilities nersc` | `references/NERSC.md` |
| ALCF (Polaris) | `https://api.alcf.anl.gov` | `scripts/token_manager.py ensure --facilities alcf` | `references/ALCF.md` |

**Before doing any work**, read the reference file for the relevant site. Do not proceed from memory.

Use the unified token manager for both sites. By default it can manage both NERSC and ALCF tokens together, but when the user is focused on one site, scope it with `--facilities nersc` or `--facilities alcf`.

`--facility` is a global flag on `iri_api_call.py` and must come before the subcommand:

```bash
# Correct
python3 scripts/iri_api_call.py --facility nersc call --operation-id getProjects --ensure-token
python3 scripts/iri_api_call.py --facility alcf call --operation-id launchJob ...

# Wrong
python3 scripts/iri_api_call.py call --facility nersc --operation-id getProjects
```

`--base-url` and `--openapi-url` follow the same rule: they are global flags and must also come before the subcommand.

## Quick Start

1. Check token state:
```bash
python3 scripts/token_manager.py status --json
```

2. Ensure a usable token for authenticated endpoints:
```bash
python3 scripts/token_manager.py ensure --min-ttl 300
```

If the IRI API still returns `401`, force a fresh identity-provider login:
```bash
python3 scripts/token_manager.py ensure --force-login --prompt-login --validate-iri
```

3. List available operations from OpenAPI:
```bash
python3 scripts/iri_api_call.py --facility nersc list-operations
python3 scripts/iri_api_call.py --facility alcf list-operations
```

4. Call an endpoint by `operationId`:
```bash
python3 scripts/iri_api_call.py --facility nersc call --operation-id getResources
python3 scripts/iri_api_call.py --facility alcf call --operation-id getResources
```

## Token Management

Use `scripts/token_manager.py` for all token lifecycle actions.

- Check token state:
```bash
python3 scripts/token_manager.py status --json
python3 scripts/token_manager.py status --facilities nersc --json
python3 scripts/token_manager.py status --facilities alcf --json
```

- Ensure usable tokens:
```bash
python3 scripts/token_manager.py ensure --min-ttl 300
python3 scripts/token_manager.py ensure --facilities nersc --min-ttl 300
python3 scripts/token_manager.py ensure --facilities alcf --min-ttl 300
```

- Refresh or login for selected facilities only:
```bash
python3 scripts/token_manager.py ensure --facilities nersc --refresh-only
python3 scripts/token_manager.py ensure --facilities alcf --refresh-only
```

- Validate the facility token against the matching API:
```bash
python3 scripts/token_manager.py ensure --facilities nersc --validate-iri --validate-facility nersc
python3 scripts/token_manager.py ensure --facilities alcf --validate-iri --validate-facility alcf
```

- Print selected facility access tokens:
```bash
python3 scripts/token_manager.py ensure --print-token
python3 scripts/token_manager.py ensure --facilities alcf --print-token
```

Notes:
- Default token file: `~/.globus/auth_tokens.json`
- The saved file preserves the full Globus token response, including `other_tokens`.
- The usable IRI API bearer token is extracted from `other_tokens`, not the top-level Globus Auth token.
- Required scopes are enforced by script validation.
- `globus-sdk` is required for refresh/login operations.
- If validation reports empty `session_info.authentications`, re-run with `--force-login --prompt-login` and complete the flow in a Chrome incognito window.

## Endpoint Execution

Use `scripts/iri_api_call.py` for all API calls.

### Operation Discovery

- List all operations:
```bash
python3 scripts/iri_api_call.py --facility nersc list-operations
python3 scripts/iri_api_call.py --facility alcf list-operations
```

- See generated static reference:
`references/operations.md`

### Public Endpoints (No Token Required)

Examples:
```bash
python3 scripts/iri_api_call.py --facility nersc call --operation-id getFacility
python3 scripts/iri_api_call.py --facility nersc call --operation-id getIncidents
python3 scripts/iri_api_call.py --facility nersc call --operation-id getResource --path-param resource_id=perlmutter
```

### Authenticated Endpoints (Token Required)

Use `--ensure-token` so calls auto-refresh/login if needed.

- Account / project context:
```bash
python3 scripts/iri_api_call.py --facility nersc call --operation-id getProjects --ensure-token
python3 scripts/iri_api_call.py --facility alcf call --operation-id getProjects --ensure-token
```

- Submit compute job (request body from file):
```bash
python3 scripts/iri_api_call.py --facility nersc call \
  --operation-id launchJob \
  --path-param resource_id=perlmutter \
  --json-file /path/to/job.json \
  --ensure-token
```

- Query one job:
```bash
python3 scripts/iri_api_call.py --facility nersc call \
  --operation-id getJob \
  --path-param resource_id=perlmutter \
  --path-param job_id=12345 \
  --ensure-token
```

- Cancel job:
```bash
python3 scripts/iri_api_call.py --facility nersc call \
  --operation-id cancelJob \
  --path-param resource_id=perlmutter \
  --path-param job_id=12345 \
  --ensure-token
```

- Filesystem list/view:
```bash
python3 scripts/iri_api_call.py --facility nersc call \
  --operation-id ls \
  --path-param resource_id=perlmutter \
  --query path=/global/cfs/cdirs \
  --ensure-token

python3 scripts/iri_api_call.py --facility nersc call \
  --operation-id view \
  --path-param resource_id=perlmutter \
  --query path=/path/to/file.txt \
  --ensure-token
```

- Upload file:
```bash
python3 scripts/iri_api_call.py --facility nersc call \
  --operation-id upload \
  --path-param resource_id=perlmutter \
  --query path=/path/on/resource/target.dat \
  --upload-file /local/path/source.dat \
  --ensure-token
```

- Poll task state:
```bash
python3 scripts/iri_api_call.py --facility nersc call --operation-id getTasks --ensure-token
python3 scripts/iri_api_call.py --facility nersc call --operation-id getTask --path-param task_id=<task_id> --ensure-token
```

## Shared Parameter Rules

- Prefer `--operation-id` over manual `--method/--path`.
- Provide required path params via repeated `--path-param key=value`.
- Provide query params via repeated `--query key=value`.
- Use one of:
  - `--json-file /path/to/body.json`
  - `--json-body '{"key":"value"}'`
  - `--upload-file /path/to/local.file` for multipart endpoints
- For binary or large outputs, use `--output-file /path/to/out.bin`.
- Use `--facility nersc` or `--facility alcf` on `scripts/iri_api_call.py` so the API server and bearer token selection stay aligned.

## Job Construction Guidance

Before generating a compute job request, check whether the user wants any of the following:
- A multistep job with multiple `srun` or `mpiexec` lines.
- Additional job-control behavior that is not covered by the API `attributes` fields.
- Explicit affinity or binding control beyond the basic resource request.

If any of those are needed, use a `pre_launch` or `post_launch` script to carry that logic instead of trying to force it into a single launch line or into unsupported `attributes`.

Rules for these scripts:
- Do not include `#SBATCH` or `#PBS` directives in `pre_launch` or `post_launch`.
- The scheduler directives belong in the batch script generated by the API server, not inside the pre/post scripts.
- Put extra `srun` or `mpiexec` lines, affinity settings, environment setup, and teardown logic in those scripts as plain shell commands.
- For NERSC-oriented launch structure and Slurm examples, use `https://docs.nersc.gov/jobs/examples/`.
- For ALCF-oriented launch structure and PBS examples, use `https://docs.alcf.anl.gov/running-jobs/example-job-scripts/#cpu-mpi-openmp-examples`.

## Reproducibility and Reference Refresh

Regenerate endpoint reference after OpenAPI updates:

```bash
python3 scripts/generate_operation_reference.py \
  --openapi references/openapi.json \
  --output references/operations.md
```

Regenerate request payload templates:

```bash
python3 scripts/generate_examples.py
```

Use templates from `references/examples/`:
- `compute-launch-job.json`
- `compute-status-filters.json`
- `filesystem-mkdir.json`
- `filesystem-mv.json`
- `filesystem-cp.json`
- `filesystem-compress.json`
- `filesystem-extract.json`
- `filesystem-chmod.json`
- `filesystem-chown.json`

Example calls using generated templates:

```bash
python3 scripts/iri_api_call.py --facility nersc call \
  --operation-id launchJob \
  --path-param resource_id=perlmutter \
  --json-file references/examples/compute-launch-job.json \
  --ensure-token

python3 scripts/iri_api_call.py --facility nersc call \
  --operation-id mkdir \
  --path-param resource_id=perlmutter \
  --json-file references/examples/filesystem-mkdir.json \
  --ensure-token
```

## Useful Endpoint Groups

- Facility + status (public): infrastructure metadata and incident visibility.
- Account (auth): user projects and allocation hierarchy.
- Compute (auth): submit/update/status/cancel jobs.
- Filesystem (auth): list/read/write/upload/download and file operations.
- Task (auth): check asynchronous task progress and cleanup.
