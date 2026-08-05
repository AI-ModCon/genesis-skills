---
name: amsc-data-movement-api
description: Use the AmSC movement API at https://api.american-science-cloud.org/api/current to list transfers, submit tutorial transfers, inspect transfer status, and cancel completed or active transfers through the provided Python client.
license: MIT
compatibility: Requires globus-sdk >= 4 (pip install 'globus-sdk>=4'); the bundled client does not run against globus-sdk 3.x
metadata:
  author: American Science Cloud Intelligent Interfaces Team
---

# AmSC Data Movement API

Use this skill when you need to work with the AmSC movement API at `https://api.american-science-cloud.org/api/current`.

This skill is currently focused on the **movement transfer** surface. The confirmed API routes, working payloads, and tutorial collection examples are captured in the companion markdown files in this skill directory.

## What the agent should do

1. Use `scripts/amsc_service_client.py` as the default client.
2. Treat `references/endpoints.md` as the source of truth for confirmed routes.
3. Use `references/examples.md` for the known-good tutorial collection IDs and transfer payloads.
4. Use `examples/curl-examples.md` when you need raw HTTP requests instead of the Python client.
5. If the client prompts for interactive Globus login, copy the login URL into `login.tmp` so the user can complete auth and return the authorization code.

## Current configuration

```text
Base URL: https://api.american-science-cloud.org/api/current
Resource server: 35bf38d3-4b30-42c8-ac9f-e39cec6516bf
Primary scope: https://auth.globus.org/scopes/35bf38d3-4b30-42c8-ac9f-e39cec6516bf/amsc
Client script: .claude/skills/amsc-data-movement-api/scripts/amsc_service_client.py
Token cache: .claude/skills/amsc-data-movement-api/scripts/tokens.json (written next to the client script — live credentials, never commit)
```

## Confirmed commands

The client currently supports these five commands:

1. `--transfers`
2. `--start-transfer '<TransferInputs JSON>'`
3. `--start-globus-transfer '<GlobusTransferInputs JSON>'`
4. `--get-globus-transfer TRANSFER_ID`
5. `--delete-globus-transfer TRANSFER_ID`

## Known working tutorial flow

The following tutorial collections are confirmed in this repo:

- Source: `6c54cade-bde5-45c1-bdea-f4bd71dba2cc`
- Destination: `31ce9ba0-176d-45a5-add3-f37d233ba47d`
- Source path: `/home/share/godata/`
- Destination path: `~/`

Both of these transfer creation paths have succeeded in live testing:

- `POST /movement/transfer`
- `POST /movement/transfer/globus`

The direct Globus route may temporarily return `409` if an identical transfer is already in progress. Retrying after the earlier transfer completes is sufficient.

## Files in this skill

- `references/authentication.md` - login flow, token cache, and consent behavior
- `references/endpoints.md` - confirmed transfer routes and payload shapes
- `references/examples.md` - tutorial collection IDs and ready-to-run examples
- `examples/curl-examples.md` - raw curl examples for all confirmed routes
- `scripts/amsc_service_client.py` - Python client for the AmSC API
