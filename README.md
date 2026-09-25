# Genesis Skills

**Portable AI-agent workflows for science and engineering**

Genesis Skills is a collection of reusable [Agent Skills](https://agentskills.io) for scientific discovery and engineering workflows. Part of the [Genesis Mission](https://gitlab.osti.gov/genesis), the catalog can be used with Claude Code, Codex, Cursor, OpenCode, Gemini CLI, and LangChain Deep Agents. Individual skills may still depend on client-specific features or external tools.

Skills encode domain expertise, connect to scientific data sources, and provide reproducible patterns for computational research.

---

## What Are Skills?

Skills are markdown files (`SKILL.md`) with YAML frontmatter that teach an AI agent how to handle domain-specific tasks. Each skill provides:

- **Domain expertise** — Specialized knowledge for literature, HPC, plasma simulation, scientific-data metadata, and AI-system evaluation
- **Tool access** — Permissions to use specific tools (Bash commands, file operations, web APIs)
- **Structured workflows** — Step-by-step instructions for complex scientific tasks
- **Supporting resources** — Scripts, templates, and reference materials the agent can use

Agents can select a skill from a natural-language request. Client-specific menus and explicit invocation shortcuts vary by agent.

---

## Quick Start

There's nothing to compile: clone the repo, then expose the skills to your agent.
The repository groups skills by domain (`skills/<domain>/<skill>/`), while agent
clients generally expect each skill to be a direct child of a configured skills
directory. `unpack.sh` flattens that layout. LangChain Deep Agents receive a
catalog path in code instead of discovering a user-level directory automatically.

```bash
git clone https://gitlab.osti.gov/genesis/genesis-skills.git
cd genesis-skills
```

> Mirror repository: The repository `https://gitlab.osti.gov/genesis/genesis-skills.git`
> is a read-only mirror of the upstream development repository
> `https://github.com/AI-ModCon/genesis-skills`. Please use GitHub for development,
> forks, issues, and pull requests.

### Method 1 — Flatten skills into place (`unpack.sh`)

Choose the skills directory documented by your client, then let `unpack.sh`
flatten every skill into it:

```bash
export SKILLS_DIR="$HOME/.agents/skills"  # Codex, Cursor, OpenCode, Gemini CLI
# export SKILLS_DIR="$HOME/.claude/skills"  # Claude Code
./unpack.sh --target "$SKILLS_DIR" --mode copy
```

Use `--mode symlink` for live links back to the clone, `./unpack.sh hpc-skills`
for one domain, `./unpack.sh --list` to preview, or `./unpack.sh --help` for all
options. The legacy default remains `.claude/skills`; an explicit `--target` is
the client-neutral choice. Existing same-named destination entries are replaced.

### Method 2 — Point the `skill-search` skill at the catalog

Expose just the bundled `skill-search` skill; it discovers the whole nested catalog
on demand, either via standard progressive disclosure or a keyword search tool:

```bash
mkdir -p "$SKILLS_DIR"
ln -s "$PWD/skill-search" "$SKILLS_DIR/skill-search"
```

`skill-search` finds the catalog automatically (sibling `skills/`), or set
`SKILL_SEARCH_CENTRAL_ROOT` / pass `--central-root` to point at a shared clone.

### Use a Skill

Ask naturally, for example: “Find recent papers on machine-learning interatomic
potentials” or “Draft a Slurm script for four GPUs.” Your client can select the
matching skill from its description. If a newly installed skill is not noticed
immediately, follow the client's documented refresh behavior.


### Discovery Helper
- `skill-search` — Discover and explore available skills by capability

---



## Repository Structure

```
genesis-skills/
├── unpack.sh                  # flatten skills into an agent's skills dir (Method 1)
├── skill-search/              # the upper-level discovery skill (Method 2)
│   ├── SKILL.md
│   └── scripts/skill_search.py
├── skills/
│   ├── academy/SKILL.md
│   ├── amsc-skills/  # amsc-data-movement-api, amsc-python-client, globus-compute, i2-api, iri-api, skill-explorer (6)
│   ├── basedata-skills/  # croissant-validator, datacard-generator, hdmf-schema-builder, skill-creator, well-convert (5)
│   ├── baseeval-skills/  # card-eval-updater, configuration-creator, configuration-implementor, configuration-planner, configuration-tester, data-exploration, perlmutter-nemo-eval, perlmutter-nemo-generate (8)
│   ├── basesafe-skills/  # agentic-vulnerabilities-scan, ai-fingerprint, battleprint, fingerprinting, uncertainty-quantification, uq-metrics-evaluator (6)
│   ├── hpc-skills/  # aurora, frontier, pbs, perlmutter, slurm (5)
│   ├── literature-search/SKILL.md
│   ├── multi-agent-systems/SKILL.md
│   └── plasma-sim-skills/  # gkeyll, gs2 (2)
├── CONTRIBUTING.md
├── LICENSE
├── NOTICE                     # third-party licensing and attribution inventory
├── README.md
└── skill_spec.md              # Agent Skills format specification
```

Each skill is a directory containing:
- `SKILL.md` — Required entry point with frontmatter and instructions
- Supporting files — Optional templates, scripts, and reference docs

---

## The Genesis Mission

Genesis is building the next generation of AI-powered tools for science and engineering. Our goals:

1. **Democratize AI for Science** — Make advanced AI capabilities accessible to researchers regardless of ML expertise
2. **Accelerate Discovery** — Reduce time from hypothesis to insight through intelligent automation
3. **Ensure Reproducibility** — Build tools that produce reliable, validated, and reproducible results
4. **Foster Collaboration** — Create a shared ecosystem where domain experts contribute and benefit from collective capabilities

---

## Contributing

We welcome contributions from the scientific community. See the [Contributing Guide](CONTRIBUTING.md) for details on:
- Skill specification format
- Testing guidelines
- Review process

If you are adding a new skill, use the checklist in [CONTRIBUTING.md](CONTRIBUTING.md) and the pull request template in [.github/pull_request_template.md](.github/pull_request_template.md) before opening the PR.

## Contributors

Individual skills and their directories contain specific attribution details. The catalog-level and skill contributors include the following:

- Matt Baughman
- Jean Luca Bez
- Eric Chagnon
- Jong Choi
- Shreyas Cholia
- Robin Cosbey
- David Florey
- Ian Foster
- Steven Goldenberg
- Nathan Hodas
- Natalie Isenberg
- Olivera Kotevska
- Fernando Llorente
- Kyle Parfrey
- Reilly Raab
- Emily Saldanha
- Malachi Schram
- Andrew Tritt
- Aaron Tuor
- Rohith Varikoti
- Stefan Wild
- American Science Cloud Intelligent Interfaces Team
- ModCon Base CAF Team
- ModCon Base Data Team
- ModCon Base Eval Team
- ModCon Base Safe Team

---

## License
This product is licensed under the root [LICENSE](LICENSE) found at the root of
this repository.
Some skills under `skills/` are sourced from third parties. Where a `LICENSE`
(or `LICENSE.txt`) file is present in a subdirectory, that license governs the
contents of that subdirectory and supersedes the root license for that subtree.
The repository-level summary of individual skill and third-party licensing
details is in [NOTICE](NOTICE); see the attribution file in each identified
subtree for the licensing information supplied with that content.

## Acknowledgment
This work was supported by the U.S. Department of Energy (DOE), Office of Science, Office of Advanced Scientific Computing Research in alignment with DOE's Genesis Mission.
