# Attribution

The skills in this directory belong to the **ModCon Base Data** project. `skill-creator` is maintained in this directory. The other four were sourced from the upstream repository below.

**Original repository:** https://github.com/AI-ModCon/BaseData_Skills

**Team:** ModCon Base Data (AI-ModCon)

These skills were retrieved from the `skills/` directory of the upstream repository and are included here as retrieved, with two frontmatter corrections applied in this catalog: a missing `name:` field was added to `well-convert`, and `datacard-generator`'s `name:` was aligned with its directory name (upstream: `generating-datacards`) with its description quoted for strict YAML parsers. The skills are otherwise unmodified. No explicit license was found in the upstream repository at the time of inclusion. Please refer to the original repository for the most current licensing information and terms of use.

Skills included:
- `croissant-validator` — Validate and generate Croissant metadata for ML datasets (MLCommons Croissant 1.0 spec)
- `datacard-generator` — Generate MODCON data cards at readiness levels L1–L3
- `hdmf-schema-builder` — Create HDMF schemas for organizing HDF5 data files
- `well-convert` — Convert a simulation dataset to the Well HDF5 format (preprocess, inspect, plan, generate scripts, run, monitor)

Maintained here (not sourced from the upstream repository):
- `skill-creator` — Author a new Agent Skill (a `SKILL.md` directory) from a template and save it where the agent discovers it
- `coding` — Rules and procedures for writing, changing, and removing code: simplicity, encapsulation, failure handling, structure, verification, and the commit procedure
- `documentation` — Which document holds a fact, and the shape of a docstring, comment, README, repository `CLAUDE.md`, development plan, and decision-log entry
- `cleanup` — Bring a repository's documents, memories, and `CLAUDE.md` back in line with its code, with a mechanical drift check and a ledger
- `autodocs` — Set up or extend a MkDocs documentation site with the API reference generated from docstrings and a strict CI build
- `write-like-aaron` — Direct technical prose for papers, READMEs, docstrings, comments, commit messages, and replies
