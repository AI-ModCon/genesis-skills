# curl Examples

Use these examples when you want raw HTTP requests instead of the Python client.

## Environment

```bash
export AMSC_API_BASE="https://api.american-science-cloud.org/api/current"
export AMSC_GLOBUS_BEARER_TOKEN="<INSERT_GLOBUS_BEARER_TOKEN>"
AUTH_HEADER="Authorization: Bearer ${AMSC_GLOBUS_BEARER_TOKEN}"
JSON_HEADER="Accept: application/json"
```

## List transfers

```bash
curl -sS \
  -H "${AUTH_HEADER}" \
  -H "${JSON_HEADER}" \
  "${AMSC_API_BASE}/movement/transfer"
```

## Create transfer with URL-style inputs

```bash
curl -sS \
  -X POST \
  -H "${AUTH_HEADER}" \
  -H "${JSON_HEADER}" \
  -H "Content-Type: application/json" \
  -d '{
    "label": "Copilot Tutorial Transfer",
    "source_url": "globus://6c54cade-bde5-45c1-bdea-f4bd71dba2cc/home/share/godata/",
    "destination_url": "globus://31ce9ba0-176d-45a5-add3-f37d233ba47d/~/"
  }' \
  "${AMSC_API_BASE}/movement/transfer"
```

## Create transfer with explicit Globus inputs

```bash
curl -sS \
  -X POST \
  -H "${AUTH_HEADER}" \
  -H "${JSON_HEADER}" \
  -H "Content-Type: application/json" \
  -d '{
    "label": "Copilot Tutorial Globus Transfer",
    "source_uuid": "6c54cade-bde5-45c1-bdea-f4bd71dba2cc",
    "source_path": "/home/share/godata/",
    "destination_uuid": "31ce9ba0-176d-45a5-add3-f37d233ba47d",
    "destination_path": "~/"
  }' \
  "${AMSC_API_BASE}/movement/transfer/globus"
```

## Get transfer status

```bash
curl -sS \
  -H "${AUTH_HEADER}" \
  -H "${JSON_HEADER}" \
  "${AMSC_API_BASE}/movement/transfer/globus/<TRANSFER_ID>"
```

## Cancel/delete a transfer

```bash
curl -sS \
  -X DELETE \
  -H "${AUTH_HEADER}" \
  -H "${JSON_HEADER}" \
  "${AMSC_API_BASE}/movement/transfer/globus/<TRANSFER_ID>"
```

## Notes

- The Python client is preferred because it manages the interactive Globus login flow.
- The direct Globus creation route can temporarily return `409` if a matching transfer is still active.
