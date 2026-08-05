# Contributing to Genesis Skills

Thank you for your interest in contributing to Genesis Skills. This guide covers the [Claude Code skills format](https://code.claude.com/docs/en/skills) and our conventions for scientific applications.

---

## Quick Start

1. **Fork** the repository and clone locally
2. **Create a branch** for your skill: `git checkout -b skill/your-skill-name`
3. **Develop** your skill following the specification below
4. **Test** your skill in Claude Code
5. **Submit** a merge request for review

### Where to Add Your Skill

Skills are organized by domain in the `skills/` directory:

- **Genesis Core (3):** `skills/academy/`, `skills/literature-search/`, and
  `skills/multi-agent-systems/`
- **BaseSAFE (5):** `skills/basesafe-skills/` for AI-safety analysis workflows
- **BaseEval (7):** `skills/baseeval-skills/` for language-model evaluation
  workflows (lm-evaluation-harness configuration and running NeMo-Skills on Perlmutter)
- **HPC (5):** `skills/hpc-skills/` for Slurm, PBS, and leadership-computing systems
- **ModCon Data (4):** `skills/modcon-data-skills/` for Croissant, HDMF, data
  cards, and Well conversion
- **Plasma Simulation (2):** `skills/plasma-sim-skills/` for GS2 and Gkeyll
- **AmSC (6):** `skills/amsc-skills/` for data movement, the Python SDK,
  Globus Compute, the i2 LLM API, the IRI API, and skill discovery

Create your skill directory in the appropriate category, or start a new category if needed.

---

## Skill Structure

Each skill is a directory with `SKILL.md` as the entry point:

```
<skill-name>/
├── SKILL.md              # Main instructions (required)
├── reference.md          # Detailed documentation (optional)
├── examples/             # Example outputs (optional)
│   └── sample-output.md
└── scripts/              # Utility scripts (optional)
    └── validate.py
```

### SKILL.md Format

Every skill has YAML frontmatter followed by markdown instructions:

```yaml
---
name: climate-data-fetch
description: >
  Retrieve climate model outputs from ESGF federated archives.
  Use when fetching CMIP5, CMIP6, or E3SM data for analysis.
allowed-tools: Bash(python *), Bash(curl *), Read, Write
---

# Climate Data Retrieval

You are a climate data specialist with expertise in federated data archives
and CF conventions.

## Your Capabilities

- Search ESGF nodes for CMIP5, CMIP6, and E3SM datasets
- Validate data availability across DOE data nodes (LLNL, ANL, ORNL)
- Subset data by variable, time range, and spatial region
- Provide metadata summaries following CF conventions

## Workflow

1. **Clarify requirements**: Confirm variable, model, experiment, and time range
2. **Search availability**: Query ESGF to find matching datasets
3. **Select data node**: Prefer DOE nodes when multiple sources exist
4. **Retrieve data**: Download or generate access scripts
5. **Validate**: Check data integrity and report any quality flags

## Guidelines

- Always verify data availability before committing to a retrieval plan
- Report known data retractions or quality issues
- Include DOI and citation information with retrieved datasets
- Warn about large data volumes before initiating transfers

## Arguments

The user may provide: `$ARGUMENTS`

Expected format: `<variable> <model> [time_range]`

Examples:
- `tas CESM2` — surface temperature from CESM2, all available times
- `pr E3SM 2015-2100` — precipitation from E3SM, 2015-2100
```

---

## Frontmatter Reference

| Field | Required | Description |
|-------|----------|-------------|
| `name` | No | Skill name (defaults to directory name). Lowercase, hyphens, max 64 chars. |
| `description` | **Yes** | What the skill does and when to use it. Claude uses this to decide when to activate. Front-load key use cases; truncated at 250 chars in listings. |
| `allowed-tools` | No | Tools Claude can use without asking permission. See examples below. |
| `disable-model-invocation` | No | Set `true` to prevent automatic activation. User must invoke with `/name`. |
| `user-invocable` | No | Set `false` to hide from `/` menu. For background knowledge only. |
| `context` | No | Set `fork` to run in an isolated subagent. |
| `agent` | No | Subagent type when `context: fork`. Options: `Explore`, `Plan`, `general-purpose`. |
| `paths` | No | Glob patterns limiting when skill activates (e.g., `*.nc, *.zarr`). |

### Tool Permissions

The `allowed-tools` field grants Claude permission to use specific tools without asking:

```yaml
# Allow specific bash commands
allowed-tools: Bash(python *), Bash(curl *), Bash(sbatch *)

# Allow file operations
allowed-tools: Read, Write, Glob, Grep

# Allow web access
allowed-tools: WebFetch, WebSearch

# Combine multiple
allowed-tools: Read, Bash(python *), Bash(pytest *)
```

### Variable Substitutions

Use these placeholders in skill content:

| Variable | Description |
|----------|-------------|
| `$ARGUMENTS` | All arguments passed when invoking the skill |
| `$ARGUMENTS[N]` or `$N` | Specific argument by index (0-based) |
| `${CLAUDE_SKILL_DIR}` | Directory containing this skill's SKILL.md |
| `${CLAUDE_SESSION_ID}` | Current session ID |

### Dynamic Context Injection

Run shell commands before Claude sees the skill content:

```yaml
---
name: hpc-status
description: Check HPC job status and queue state
allowed-tools: Bash(squeue *), Bash(sacct *)
---

## Current Queue State

!`squeue -u $USER --format="%.10i %.20j %.8T %.10M %.6D %R" 2>/dev/null || echo "Queue unavailable"`

## Your Task

Based on the queue state above, help the user with: $ARGUMENTS
```

The `` !`command` `` syntax runs before Claude receives the prompt.

---

## Supporting Files

Keep `SKILL.md` focused (<500 lines). Move detailed content to supporting files:

```
my-skill/
├── SKILL.md           # Overview and main instructions
├── api-reference.md   # Detailed API documentation
├── examples.md        # Usage examples
└── scripts/
    └── helper.py      # Utility scripts Claude can execute
```

Reference supporting files from SKILL.md:

```markdown
## Additional Resources

- For ESGF API details, see [api-reference.md](api-reference.md)
- For usage examples, see [examples.md](examples.md)

To validate retrieved data, run:
```bash
python ${CLAUDE_SKILL_DIR}/scripts/validate.py <dataset_path>
```
```

---

## Writing Effective Skills

### Prompt Engineering

**Be specific about scope**
```markdown
# Good
You specialize in CMIP6 climate data from ESGF. You can search, retrieve,
and validate datasets but do not perform climate analysis.

# Too vague
You help with climate data.
```

**Include guardrails**
```markdown
## Limitations

- Do not modify existing data files without explicit confirmation
- Warn before downloads exceeding 10 GB
- Do not store credentials in scripts or outputs
```

**Show expected formats**
```markdown
## Output Format

Provide results as:

| Variable | Model | Experiment | Time Range | Data Node | Size |
|----------|-------|------------|------------|-----------|------|
| tas | CESM2 | ssp585 | 2015-2100 | llnl | 2.3 GB |
```

### Scientific Rigor

- **Cite sources** for domain knowledge embedded in prompts
- **Document assumptions** and limitations explicitly
- **Include uncertainty** when relevant
- **Prefer established methods** over novel approaches
- **Reference standards** (CF conventions, ISO formats, community schemas)

### For HPC Skills

```yaml
---
name: hpc-job-submit
description: Submit and monitor jobs on Slurm/PBS HPC systems
allowed-tools: Bash(sbatch *), Bash(squeue *), Bash(scancel *), Read, Write
disable-model-invocation: true  # User must explicitly invoke
---

# HPC Job Submission

## Safety Guidelines

- Never submit jobs without user confirmation of the job script
- Always show estimated SU cost before submission
- Limit default node count to project allocation
- Include wall time estimates based on problem size

## Workflow

1. Review or create job script
2. Validate resource requests against allocation
3. Confirm with user before submission
4. Submit and report job ID
5. Provide monitoring commands
```

---

## Running Skills in Subagents

Use `context: fork` for tasks that benefit from isolation:

```yaml
---
name: deep-literature-search
description: Comprehensive literature search across multiple databases
context: fork
agent: Explore
allowed-tools: WebSearch, WebFetch, Read, Write
---

# Literature Search Agent

Conduct a thorough literature search for: $ARGUMENTS

## Search Strategy

1. Search Google Scholar, arXiv, and PubMed
2. Identify seminal papers and recent advances
3. Map citation relationships
4. Synthesize findings into a structured report

## Output

Create a markdown report with:
- Executive summary
- Key papers (with citations)
- Research gaps
- Suggested reading order
```

---

## Example Skills

### Minimal Skill

```yaml
---
name: fortran-help
description: Help with Fortran code, focusing on modern Fortran best practices
---

You are a Fortran expert specializing in modern Fortran (2003/2008/2018).

When helping with Fortran code:
- Prefer modern constructs over legacy patterns
- Use modules and explicit interfaces
- Recommend `implicit none` in all scopes
- Suggest array operations over explicit loops where appropriate
```

### Skill with Scripts

```yaml
---
name: netcdf-inspect
description: Inspect and summarize NetCDF file structure and contents
allowed-tools: Bash(python *), Read
---

# NetCDF Inspector

Analyze NetCDF files and provide structured summaries.

## Quick Inspection

Run the bundled inspection script:

```bash
python ${CLAUDE_SKILL_DIR}/scripts/inspect_nc.py $ARGUMENTS
```

## Manual Analysis

For detailed analysis, I can:
- List dimensions, variables, and attributes
- Check CF convention compliance
- Identify coordinate systems
- Report data ranges and missing values
```

---

## Testing Your Skill

### Manual Testing

1. Install the skill in your Claude Code skills directory
2. Start a new Claude Code session
3. Check the skill is recognized: "What skills are available?"
4. Test invocation: `/your-skill-name test arguments`
5. Test automatic activation with matching prompts

### Test Cases to Cover

- **Happy path**: Skill works with valid inputs
- **Edge cases**: Missing arguments, unusual inputs
- **Error handling**: Invalid data, network failures
- **Guardrails**: Skill refuses inappropriate requests

---

## Merge Request Process

### Before Submitting

- [ ] `SKILL.md` has a clear, specific description
- [ ] Instructions are tested in Claude Code
- [ ] Supporting files are referenced from SKILL.md
- [ ] No sensitive data or credentials in code
- [ ] Scientific claims include citations or references

### Review Criteria

1. **Usefulness** — Does this skill address a real research need?
2. **Correctness** — Is the domain knowledge accurate?
3. **Safety** — Are appropriate guardrails in place?
4. **Clarity** — Are instructions unambiguous?
5. **Composability** — Can it work alongside other skills?

### Naming Conventions

- Use lowercase with hyphens: `climate-data-fetch`, not `ClimateDataFetch`
- Be specific: `cmip6-search` rather than `data-search`
- Include domain when helpful: `mpi-debug`, `slurm-submit`
- Choose the appropriate skills category (see "Where to Add Your Skill" above)
- If your skill spans multiple domains, discuss placement in your merge request

---

## Community Guidelines

### Communication

- Use GitLab issues for bugs and feature requests
- Tag issues appropriately: `new-skill`, `bug`, `enhancement`
- Be respectful and constructive

### Collaboration

- Credit contributors in skill descriptions
- Build on existing skills rather than duplicating
- Share learnings with the community

---

## Recognition

Contributors are recognized through:
- Author credits in skill metadata
- Acknowledgment in release notes
- Invitation to Genesis community events

We value all contributions—new skills, improvements, documentation, and feedback.
