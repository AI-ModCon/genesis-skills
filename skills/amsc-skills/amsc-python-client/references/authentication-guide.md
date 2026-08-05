# Authentication Guide

## Scripted Auth (Recommended for Claude)

Use `scripts/token_manager.py` for all auth lifecycle management.

### Check Status
```bash
python3 .claude/skills/amsc-python-client/scripts/token_manager.py status --json
```

### Ensure Token (Auto-Refresh or Login)
```bash
# ALCF
python3 .claude/skills/amsc-python-client/scripts/token_manager.py ensure alcf

# NERSC
python3 .claude/skills/amsc-python-client/scripts/token_manager.py ensure nersc

# AmSC gateway (catalog, workflows)
python3 .claude/skills/amsc-python-client/scripts/token_manager.py ensure amsc

# With validation against API
python3 .claude/skills/amsc-python-client/scripts/token_manager.py ensure nersc --validate

# Force fresh login
python3 .claude/skills/amsc-python-client/scripts/token_manager.py ensure alcf --force-login
```

### Clear Cached Tokens
```bash
python3 .claude/skills/amsc-python-client/scripts/token_manager.py clear alcf
python3 .claude/skills/amsc-python-client/scripts/token_manager.py clear nersc
python3 .claude/skills/amsc-python-client/scripts/token_manager.py clear all
```

### Interactive Login Flow

When `ensure` triggers a login, it:
1. Prints a Globus authorization URL
2. Waits for user to paste the auth code
3. Caches tokens at `~/.amsc/credentials.json` (600 permissions)

Tell the user to run it interactively:
```
! python3 .claude/skills/amsc-python-client/scripts/token_manager.py ensure nersc
```

## SDK Auth Methods

### Token Authentication (Simplest)

```python
client = Client(token="your-api-token")
```
Static bearer token. No refresh. Best for CI/CD or service accounts.

### Globus OAuth2 (Interactive)

```python
app_id = "e4f48665-38b5-4833-a89e-849c71f5b3e3"
client = Client(
    auth_method="globus",
    globus_client_id=app_id,
    requested_scopes=f"openid profile email https://auth.globus.org/scopes/{app_id}/amsc_test",
    resource_server=app_id,
    use_id_token=True,
)
```

- Browser-less: prints URL + waits for auth code
- Tokens cached at `~/.amsc/credentials.json`
- Auto-refresh via refresh tokens (60s buffer before expiry)

### Ping Identity Device Flow (Headless)

```python
client = Client(
    auth_method="ping",
    ping_issuer_url="https://your-ping-issuer.example.com",
    ping_client_id="your-ping-client-id",
)
```

## Facility Auth

**ALCF** is built-in. **NERSC** requires manual registration (not in SDK v0.4.x):

```python
client = Client(token="placeholder")
alcf = client.facility("alcf")    # Built-in, works immediately

# NERSC — register first (see SKILL.md Quick Start or use register_nersc.py)
exec(open(".claude/skills/amsc-python-client/scripts/register_nersc.py").read())
register_nersc(client)
nersc = client.facility("nersc")
```

Each facility has its own authenticator. Authenticating to ALCF does NOT authenticate to NERSC.

### Globus Credentials (Built-in)

| Facility | Client ID | Scope |
|----------|-----------|-------|
| ALCF | `8b84fc2d-49e9-49ea-b54d-b3a29a70cf31` | `filesystem` scope |
| NERSC | `fae5c579-490a-4d76-b6eb-d78f65caeb63` | `iri_api` scope |

## Config File (`~/.amsc/config.yaml`)

```yaml
base_url: https://api.american-science-cloud.org/api/current
auth_method: globus
globus_client_id: "e4f48665-38b5-4833-a89e-849c71f5b3e3"
```

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `AMSC_BASE_URL` | API base URL |
| `AMSC_TOKEN` | Static token |
| `AMSC_AUTH_METHOD` | `token`, `globus`, or `ping` |
| `AMSC_GLOBUS_CLIENT_ID` | Globus native app ID |

**Priority:** Constructor args > env vars > config file > defaults

## Token Caching

- Tokens stored in `~/.amsc/credentials.json` (keyed by `globus_{client_id}`)
- Refresh 60 seconds before expiration
- On 401: auto-retry after refresh (via `retry_on_401` decorator)

## Troubleshooting

### Persistent 401 Errors
```bash
python3 .claude/skills/amsc-python-client/scripts/token_manager.py clear all
python3 .claude/skills/amsc-python-client/scripts/token_manager.py ensure <target> --force-login
```

Also clear browser cookies for `globus.org` and `globusid.org`.

**Root cause (ALCF):** Embedded Keycloak identity token can expire while Globus token remains valid.

### Auth Not Triggering
Authentication is lazy — no login until a protected endpoint is called. Use `token_manager.py ensure` to pre-authenticate.
