# NERSC IRI API

**Base URL:** `https://api.iri.nersc.gov` (default for `iri_api_call.py`)

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
python3 scripts/iri_api_call.py list-operations
```

4. Call an endpoint by `operationId`:
```bash
python3 scripts/iri_api_call.py call --operation-id getResources
```

## Token Management

Use `scripts/token_manager.py` for all token lifecycle actions.

- Inspect existing token:
```bash
python3 scripts/token_manager.py status
```

- Refresh or login only when needed:
```bash
python3 scripts/token_manager.py ensure --min-ttl 300
```

- Force new interactive consent flow:
```bash
python3 scripts/token_manager.py ensure --force-login
```

- Force a fresh IdP login prompt when server-side session state is bad:
```bash
python3 scripts/token_manager.py ensure --force-login --prompt-login
```

- Refresh saved tokens only, without opening a browser:
```bash
python3 scripts/token_manager.py ensure --refresh-only
```

- Validate the IRI bearer token against the API:
```bash
python3 scripts/token_manager.py ensure --validate-iri
```

- Emit machine-readable token metadata:
```bash
python3 scripts/token_manager.py ensure --json
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
python3 scripts/iri_api_call.py list-operations
```

- See generated static reference:
`references/operations.md`

### Public Endpoints (No Token Required)

Examples:
```bash
python3 scripts/iri_api_call.py call --operation-id getFacility
python3 scripts/iri_api_call.py call --operation-id getIncidents
python3 scripts/iri_api_call.py call --operation-id getResource --path-param resource_id=perlmutter
```

### Authenticated Endpoints (Token Required)

Use `--ensure-token` so calls auto-refresh/login if needed.

- Account / project context:
```bash
python3 scripts/iri_api_call.py call --operation-id getProjects --ensure-token
```

- Submit compute job (request body from file):
```bash
python3 scripts/iri_api_call.py call \
  --operation-id launchJob \
  --path-param resource_id=perlmutter \
  --json-file /path/to/job.json \
  --ensure-token
```

For NERSC jobs, put the queue or QOS selection in `attributes.queue_name`. Examples:
- `debug`
- `regular`
- `express_amsc_g`

Do not try to set NERSC QOS with `attributes.custom_attributes.qos`; the API path that worked in testing was `attributes.queue_name`.

- Query one job:
```bash
python3 scripts/iri_api_call.py call \
  --operation-id getJob \
  --path-param resource_id=perlmutter \
  --path-param job_id=12345 \
  --ensure-token
```

- Cancel job:
```bash
python3 scripts/iri_api_call.py call \
  --operation-id cancelJob \
  --path-param resource_id=perlmutter \
  --path-param job_id=12345 \
  --ensure-token
```

- Filesystem list/view:

  Use the storage resource name that matches the path prefix — **not** `perlmutter`:

  | Path prefix | `resource_id` to use |
  |---|---|
  | `/global/homes/` or `/global/u1/` | `homes` |
  | `/pscratch/` | `scratch` |
  | `/global/cfs/` | `cfs` |
  | `/global/common/` | `common` |

```bash
RESOURCE=<homes|scratch|cfs|common>   # pick based on path prefix above

python3 scripts/iri_api_call.py call \
  --operation-id ls \
  --path-param resource_id=$RESOURCE \
  --query path=/path/to/directory \
  --ensure-token

python3 scripts/iri_api_call.py call \
  --operation-id view \
  --path-param resource_id=$RESOURCE \
  --query path=/path/to/file.txt \
  --ensure-token
```

- Upload file:
```bash
RESOURCE=<homes|scratch|cfs|common>   # pick based on destination path prefix

python3 scripts/iri_api_call.py call \
  --operation-id upload \
  --path-param resource_id=$RESOURCE \
  --query path=/path/on/resource/target.dat \
  --upload-file /local/path/source.dat \
  --ensure-token
```

- Poll task state:
```bash
python3 scripts/iri_api_call.py call --operation-id getTasks --ensure-token
python3 scripts/iri_api_call.py call --operation-id getTask --path-param task_id=<task_id> --ensure-token
```

## Path Rules for Job and Filesystem Specs

**Never use shell variables (`$HOME`, `$SCRATCH`, `$USER`) in job or filesystem JSON bodies.** The IRI API passes these values as literal strings — they are not expanded by the shell or by Slurm. Use absolute paths instead.

Perlmutter home directories follow the pattern `/global/homes/<first-letter>/<username>` (for example `/global/homes/u/username`). Scratch is at `/pscratch/sd/<first-letter>/<username>`.

Always substitute real paths before submitting. The example templates use `<first-letter>/<username>` placeholders — replace them with actual values.

## Useful Resource IDs

The NERSC `getResources` output is broad, but these are the IDs worth remembering for common work:

| Name | Resource ID | Type | Notes |
|---|---|---|---|
| `perlmutter` compute via `launchJob` path param | `perlmutter` | compute alias | Use this string with compute job endpoints even though `getResources` also exposes UUID-backed compute entries |
| `compute` | `94351904-6dba-4c16-b5cd-fbd280d8615b` | compute | General compute resource entry from `getResources` |
| `login` | `e525a224-61c1-419f-9642-91168c792e39` | compute | Login nodes |
| `homes` | `65b28619-c3b6-4942-8da1-044a3b3a2a9e` | storage | Global Homes |
| `scratch` | `43d8f6c0-f900-48ce-b267-73714103f4ac` | storage | Scratch |
| `cfs` | `59e80c79-4dfd-4c53-9c07-7405685fcd37` | storage | CFS |
| `common` | `7e07a611-f927-4a39-a44d-b1d6e307accd` | storage | Global Common |
| `archive` | `f4916c65-9001-49c2-b0bf-6fe4276b564c` | storage | HPSS Archive |
| `regent` | `bc5ed17b-946e-432d-ae61-c4812a637868` | storage | Tape-oriented storage entry |
| `jobs` | `3cf3c048-855e-4dd8-a189-065a483954bb` | service/unknown | Slurm commands wrapper resource |
| `realtime` | `3776417d-747c-4753-895a-6323c17b9c98` | service/unknown | Urgent jobs wrapper resource |

Notes:
- For compute job submission, continue using `resource_id=perlmutter` as shown in the working examples.
- For filesystem endpoints, prefer the short storage names documented earlier in this file: `homes`, `scratch`, `cfs`, and `common`.
- The UUIDs above came from a live `getResources` query on April 8, 2026.

To refresh this list later:

```bash
python3 scripts/iri_api_call.py --facility nersc call --operation-id getResources
```

## OpenAPI Notes

These details are worth remembering from `references/openapi.json` so they do not need to be rediscovered each time:

- `launchJob` takes a `JobSpec` JSON body and a `resource_id` path parameter.
- Common `JobSpec` fields are:
  - `executable`
  - `arguments`
  - `directory`
  - `stdout_path`
  - `stderr_path`
  - `launcher`
  - `resources`
  - `attributes`
  - `pre_launch`
  - `post_launch`
- `resources` supports:
  - `node_count`
  - `process_count`
  - `processes_per_node`
  - `cpu_cores_per_process`
  - `gpu_cores_per_process`
  - `exclusive_node_use`
  - `memory`
- For NERSC queue or QOS selection, use `attributes.queue_name`.
- For NERSC scheduler-specific extras such as `constraint`, use `attributes.custom_attributes`.
- For multistep jobs or extra launch control, use `pre_launch` or `post_launch` and keep `#SBATCH` directives out of those scripts.
- `getJob` returns rich scheduler metadata under `status.meta_data`, including fields like `partition`, `qos`, `constraints`, `nodelist`, `stdoutPath`, and `stderrPath`.

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

In `references/examples/compute-launch-job.json`, set the queue or QOS at:

```json
"attributes": {
  "duration": 300,
  "queue_name": "debug",
  "account": "<replace-with-project-account>"
}
```

Replace `"debug"` with the queue or QOS you need, such as `"express_amsc_g"`.

Example calls using generated templates:

```bash
python3 scripts/iri_api_call.py call \
  --operation-id launchJob \
  --path-param resource_id=perlmutter \
  --json-file references/examples/compute-launch-job.json \
  --ensure-token

python3 scripts/iri_api_call.py call \
  --operation-id mkdir \
  --path-param resource_id=$RESOURCE \
  --json-file references/examples/filesystem-mkdir.json \
  --ensure-token
```
