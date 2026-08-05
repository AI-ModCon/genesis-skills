# Endpoint Inventory

This file is the source of truth for the confirmed movement API routes currently used by this skill.

## Service configuration

- Base URL: `https://api.american-science-cloud.org/api/current`
- Auth: Globus `UserApp` bearer token
- Resource server: `35bf38d3-4b30-42c8-ac9f-e39cec6516bf`
- Scope: `https://auth.globus.org/scopes/35bf38d3-4b30-42c8-ac9f-e39cec6516bf/amsc`

## Confirmed routes

| Method | Path | Purpose | Request body | Result |
| --- | --- | --- | --- | --- |
| `GET` | `/movement/transfer` | List transfers visible to the current user | none | Returns a JSON array of `{label, transfer_id}` objects |
| `POST` | `/movement/transfer` | Create a transfer from URL-style inputs | `TransferInputs` | Returns a JSON array of `{label, transfer_id}` objects |
| `POST` | `/movement/transfer/globus` | Create a transfer from explicit Globus collection/path inputs | `GlobusTransferInputs` | Returns a JSON array of `{label, transfer_id}` objects |
| `GET` | `/movement/transfer/globus/{transfer_id}` | Get status for a transfer | none | Returns a `GlobusTransferResult` object |
| `DELETE` | `/movement/transfer/globus/{transfer_id}` | Cancel/delete a transfer | none | Returns a `GlobusTransferResult` object |

## Request schemas

### `TransferInputs`

```json
{
  "label": "AmSC Transfer",
  "source_url": "globus://src-collection-uuid/home/share/godata/",
  "destination_url": "globus://dst-collection-uuid/~/"
}
```

### `GlobusTransferInputs`

```json
{
  "label": "AmSC Transfer",
  "source_uuid": "src-collection-uuid",
  "source_path": "/home/share/godata/",
  "destination_uuid": "dst-collection-uuid",
  "destination_path": "~/"
}
```

## Response schema notes

### Transfer list / create responses

```json
[
  {
    "label": "Copilot Tutorial Transfer",
    "transfer_id": "example-transfer-id"
  }
]
```

### Transfer detail / delete responses

```json
{
  "transfer_uuid": "example-transfer-id",
  "status": "SUCCEEDED",
  "completion_time": "2026-05-05T21:49:34Z",
  "reason": "",
  "bytes_transferred": 0,
  "effective_bytes_per_second": 0
}
```

## Known runtime behaviors

- `POST /movement/transfer/globus` can return `409` with `A transfer with identical paths has not yet completed` if the same source and destination are already active.
- `DELETE /movement/transfer/globus/{transfer_id}` can return a result whose embedded reason says the task already completed before cancellation.
- Both transfer creation routes have succeeded in live testing with the tutorial collections in `references/examples.md`.
