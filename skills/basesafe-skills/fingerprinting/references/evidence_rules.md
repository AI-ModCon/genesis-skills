# Evidence Rules

Fingerprinting is only useful if the claims are reviewable. Every important classification claim should include evidence and confidence.

## Evidence Priority

Prefer evidence in this order:

1. Executable code paths
2. Configs and manifests
3. Tests and evaluation scripts
4. Dependency files and lockfiles
5. README or technical docs
6. Notebooks
7. Comments or TODOs

Claims backed only by README text should usually be marked `medium` confidence unless corroborated.

## Good Evidence Examples

- `src/train.py` shows `Trainer.fit(...)` with image dataset loaders
- `config/model.yaml` defines `task: segmentation`
- `requirements.txt` includes `torch`, `torchvision`, and `monai`
- `app/server.py` exposes a FastAPI inference endpoint
- `prompts/system.txt` plus `vectordb/` implies RAG behavior

## Weak Evidence Examples

- A marketing-oriented README with no corroborating code
- A notebook copied into the repo but not referenced elsewhere
- TODO comments describing intended future architecture

## Confidence Rules

Use:
- `high` when the claim is directly evidenced and repeated across artifacts
- `medium` when there is direct but partial evidence
- `low` when the claim is mostly inferred

Lower confidence when:
- the repo is incomplete
- multiple architectures coexist
- docs and code conflict
- the model artifact is absent

## Unknowns

Prefer explicit unknowns over invented certainty. Typical unknowns:
- training data provenance
- deployment environment
- exact model architecture hidden behind proprietary wrappers
- whether docs reflect current behavior

## Evidence Format

When possible, capture:
- file path
- short note about what it shows
- optional line hint

Example:

`src/inference.py`: loads a `SentenceTransformer` and queries FAISS, suggesting embedding retrieval at inference time.

