# Catalog API Reference

## CatalogClient (`client.catalog`)

### Search

```python
results = client.catalog.search("query", limit=20)
print(results.total_count)
for item in results:
    print(item.name, item.type, item.fqn)
```

`SearchResults` supports iteration, `len()`, indexing, `.total_count`.

### Get Entity

```python
entity = client.catalog.get("catalog.container.entity-name")
print(entity.name, entity.fqn, entity.type, entity.description)
```

Returns typed wrapper: `Artifact`, `ScientificWork`, `MLModel`, `Table`, etc.

**Property aliases:** `entity.type` (not `type_`), `entity.format` (not `format_`)

### Create Scientific Work

```python
work = client.catalog.create_scientific_work(
    catalog="olcf-constellation-amsc-storage.olcf-const-data-catalog",
    name="my-research-project",
    description="Study of X",
    location="s3://bucket/data/",
)
print(work.fqn)  # use as parent for artifacts
```

### Create Artifact

```python
artifact = client.catalog.create_artifact(
    catalog="storage.catalog",
    parent=work.fqn,
    name="dataset-v1",
    description="Main dataset",
    location="s3://bucket/data/main.parquet",
    format="application/parquet",
    size=2097152,
)
```

### Update Entity

```python
updated = client.catalog.update(fqn, {"description": "Updated description"})
```

### Delete Entity

```python
client.catalog.delete(fqn)  # cascades to children for ScientificWork
```

### Transfers

```python
# List transfers
transfers = client.catalog.transfer.list()

# Globus transfer
result = client.catalog.globus_transfer.start(transfer_body)
```

## Entity Types

| Type | Class | Description |
|------|-------|-------------|
| ScientificWork | `ScientificWork` | Research project container |
| Artifact | `Artifact` | Dataset/file within a project |
| ArtifactCollection | `ArtifactCollection` | Group of related artifacts |
| MLModel | `MLModel` | Machine learning model |
| Table | `Table` | Tabular data entity |

## FQN (Fully Qualified Name)

Format: `catalog-storage.catalog-name.scientific-work.artifact`

Hierarchical dot-separated path. Used as unique identifier for all operations.

## API Endpoints

| Operation | Endpoint |
|-----------|----------|
| Search | `GET /search` |
| Get | `GET /catalog/{fqn}` |
| Create | `POST /catalog/{catalog}/{entity_type}` |
| Update | `PATCH /catalog/{fqn}` |
| Delete | `DELETE /catalog/{fqn}` |
| Transfers | `GET/POST /catalog/transfers` |
