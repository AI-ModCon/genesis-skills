# Authentication

## Base URL and scope

```text
Base URL: https://api.american-science-cloud.org/api/current
Resource server: 35bf38d3-4b30-42c8-ac9f-e39cec6516bf
Primary scope: https://auth.globus.org/scopes/35bf38d3-4b30-42c8-ac9f-e39cec6516bf/amsc
```

## Default client

Use the Python client in this skill:

```bash
python3 .claude/skills/amsc-data-movement-api/scripts/amsc_service_client.py --transfers
```

The client uses a Globus `UserApp` and stores tokens next to the client script:

```text
.claude/skills/amsc-data-movement-api/scripts/tokens.json
```

## Interactive login flow

When no valid cached token is available, the client prints a Globus authorization URL and waits for an authorization code.

Agent workflow:

1. Start the client command.
2. If a login URL is printed, allow the user to login with it
3. Wait for the user to complete the browser flow and provide the authorization code.
4. Send the code back to the waiting client process.

## Consent-required behavior

Transfer creation can require additional Globus `data_access` consent for the source collection.

For the tutorial source collection, the server has requested this composite scope during live testing:

```text
https://auth.globus.org/scopes/35bf38d3-4b30-42c8-ac9f-e39cec6516bf/amsc[urn:globus:auth:scope:transfer.api.globus.org:all[*https://auth.globus.org/scopes/6c54cade-bde5-45c1-bdea-f4bd71dba2cc/data_access]]
```

If the client prints a consent URL, treat it the same way as the initial login URL and write it to `login.tmp`.

## Notes

- Keep tokens and authorization codes out of committed files.
- The default API host for this skill is `https://api.american-science-cloud.org/api/current`.
