# Attribution

The skills in this directory were contributed by the **American Science Cloud (AmSC) Intelligent Interfaces Team**.

**Source repository:** https://gitlab.com/amsc2/ai-services/intelligent-interfaces/agent-skills

**Team:** American Science Cloud Intelligent Interfaces Team

Most of these skills target the American Science Cloud platform and the DOE facility APIs it fronts (ALCF, NERSC); `globus-compute` talks to Globus Compute / NERSC directly, and `skill-explorer` is a general cross-repo skill discovery and sync tool. Each skill's `SKILL.md` carries a `metadata.author` credit to the team. Beyond that credit, a set of small integration adaptations was made, all identified during integration audits and limited to minor corrections: path references were updated from upstream repo layouts to this catalog's install layout (`amsc-data-movement-api`, `amsc-python-client`); missing dependency and platform requirements were declared (`compatibility` frontmatter and `scripts/requirements.txt` entries for `amsc-data-movement-api`, `globus-compute`, and `i2-api`; a bash >= 4 + gawk note for `skill-explorer`); and one-to-three-line fixes were applied to mismatched defaults, help/error text, and documented commands (`skill-explorer` discover default host, `amsc-python-client` setup-check token path and auth-guide sample, `globus-compute` sample help text and install hint, `iri-api` local `--openapi` fallback and ALCF command flag order). A stray `__pycache__` was removed. The skills' content and workflows are otherwise as provided. `amsc-data-movement-api` declares the MIT license in its frontmatter; no other licensing information accompanied the skills — refer to the team for current terms.

Skills included:
- `amsc-data-movement-api` — Work with the AmSC data movement API (list, submit, inspect, and cancel transfers) via the bundled Python client
- `amsc-python-client` — Unified AmSC Python SDK: auth, data catalog, DOE facility compute/storage, filesystem ops, workflows, MLflow, and accounts
- `globus-compute` — Submit Python functions to NERSC Perlmutter via Globus Compute template-capable endpoints
- `i2-api` — AmSC i2 LLM API: key validation, model discovery and selection, chat completions, embeddings, spend tracking, and Claude Code / LangChain setup
- `iri-api` — IRI API deployments at NERSC and ALCF: Globus token lifecycle and OpenAPI-driven facility/compute/filesystem/task operations
- `skill-explorer` — Discover and sync agent skills across GitLab groups and GitHub organizations for Codex CLI, Claude Code, and OpenCode CLI
