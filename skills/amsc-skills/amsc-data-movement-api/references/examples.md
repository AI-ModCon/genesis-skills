# Tutorial Examples

## Tutorial collections

- Globus Tutorial Collection 1: `6c54cade-bde5-45c1-bdea-f4bd71dba2cc`
- Globus Tutorial Collection 2: `31ce9ba0-176d-45a5-add3-f37d233ba47d`

## Tutorial paths

- Source path: `/home/share/godata/`
- Destination path: `~/`

## Tutorial URLs

- `globus://6c54cade-bde5-45c1-bdea-f4bd71dba2cc/home/share/godata/`
- `globus://31ce9ba0-176d-45a5-add3-f37d233ba47d/~/`

## Python client examples

### List transfers

```bash
python3 .claude/skills/amsc-data-movement-api/scripts/amsc_service_client.py \
  --transfers
```

### Create transfer with URL-style inputs

```bash
python3 .claude/skills/amsc-data-movement-api/scripts/amsc_service_client.py \
  --start-transfer '{
    "label": "Copilot Tutorial Transfer",
    "source_url": "globus://6c54cade-bde5-45c1-bdea-f4bd71dba2cc/home/share/godata/",
    "destination_url": "globus://31ce9ba0-176d-45a5-add3-f37d233ba47d/~/"
  }'
```

### Create transfer with explicit Globus inputs

```bash
python3 .claude/skills/amsc-data-movement-api/scripts/amsc_service_client.py \
  --start-globus-transfer '{
    "label": "Copilot Tutorial Globus Transfer",
    "source_uuid": "6c54cade-bde5-45c1-bdea-f4bd71dba2cc",
    "source_path": "/home/share/godata/",
    "destination_uuid": "31ce9ba0-176d-45a5-add3-f37d233ba47d",
    "destination_path": "~/"
  }'
```

### Inspect a transfer

```bash
python3 .claude/skills/amsc-data-movement-api/scripts/amsc_service_client.py \
  --get-globus-transfer "<TRANSFER_ID>"
```

### Cancel/delete a transfer

```bash
python3 .claude/skills/amsc-data-movement-api/scripts/amsc_service_client.py \
  --delete-globus-transfer "<TRANSFER_ID>"
```

## Known successful live examples

- Generic transfer route succeeded with transfer ID `b201b54c-48cc-11f1-b705-0ea3589134b3`
- Direct Globus transfer route succeeded with transfer ID `fd62fc50-48cc-11f1-a7d5-0afffe4617ab`
