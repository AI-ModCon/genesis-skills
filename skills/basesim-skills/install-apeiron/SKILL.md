---
name: install-apeiron
description: >-
  Install the apeiron continual-learning package into an existing Python project
  so `import apeiron` works. Use when adding apeiron to another project or
  training framework, setting it up as a path or git dependency, or fixing
  `from apeiron import ...` elsewhere. Handles package-manager detection, Python
  version checks, and CPU-vs-CUDA PyTorch selection. Not for developing inside
  the apeiron repository itself.
compatibility: >-
  Requires Python matching apeiron's `requires-python` range (3.13 at the time
  of writing) and either Poetry or pip/uv in the target project. Needs a local
  apeiron checkout or its git URL.
metadata:
  short-description: Install apeiron into another Python project
  upstream: https://github.com/AI-ModCon/BaseSIM_APEIRON
allowed-tools: Bash Read Edit Write Glob Grep
---

# Install apeiron into another project

Install apeiron as a dependency in the user's own Python project, hands-off.

## Inputs

- **Target project directory** — the project that will depend on apeiron. Use
  the path the user gives, otherwise the current working directory.
- **Optional git URL** — when the user wants a git dependency, use that URL
  instead of a local path dependency. The canonical URL is
  `https://github.com/AI-ModCon/BaseSIM_APEIRON.git`.

Do not assume any value that was not given. Read it from the repository where
possible, and ask only when the source or target cannot be discovered safely.

## Success criteria

After this skill runs, the following must succeed from inside the target
project's environment:

```bash
python -c "from apeiron import BaseModelHarness, ContinuousMonitor, build_config; print('apeiron OK')"
```

## Procedure

### 1. Resolve the target project and its package manager

- Confirm the target directory contains a `pyproject.toml` (Poetry / PEP 621) or
  a `requirements.txt` / `setup.py` (pip). If none are present, ask the user how
  they manage dependencies.
- Detect the manager: Poetry when `[tool.poetry]` or `poetry.lock` is present,
  otherwise the existing pip or uv workflow. Poetry is the primary path below; a
  pip fallback is in step 6.

### 2. Resolve the apeiron source

Do not hardcode versions or paths.

- If the user gave a git URL, use it as the dependency source.
- Otherwise prefer a local checkout. A directory is apeiron when its
  `pyproject.toml` names the package `apeiron`:

  ```bash
  grep -m1 'name = "apeiron"' pyproject.toml && pwd
  ```

  Use that absolute path as a **path (develop) dependency**.
- If no local checkout can be found and no git URL was given, ask the user for
  the apeiron path or git URL, or offer to clone it.

### 3. Verify Python

Guide the user; do not auto-manage interpreters.

- Read apeiron's required range dynamically rather than assuming it:

  ```bash
  grep 'requires-python' <apeiron_pyproject>
  ```

- Check the interpreter the target project will use (`python --version`, or
  `poetry env info --python`). If it is outside the range, stop and give exact
  instructions — for example install the matching CPython via pyenv or uv and
  point Poetry at it with `poetry env use <path>`. Do not silently install or
  switch interpreters.

### 4. Ensure Poetry is available

For Poetry targets, check `command -v poetry`. If it is missing and installing
it is necessary, ask the user before running an install command
(`pipx install poetry` preferred, or `pip install --user poetry`), then re-check
`poetry --version` before continuing.

### 5. Detect the compute backend and select the PyTorch wheel

Probe for an NVIDIA GPU:

```bash
nvidia-smi -L 2>/dev/null && echo "GPU_PRESENT" || echo "NO_GPU"
```

- **GPU present:** do nothing special — the default CUDA-enabled torch wheels
  resolve normally. Report that CUDA wheels will be used.
- **No GPU:** pin torch to the CPU-only index so the install is smaller and
  portable. For a Poetry target, add an explicit source and route torch to it
  *before* adding apeiron:

  ```toml
  [[tool.poetry.source]]
  name = "pytorch-cpu"
  url = "https://download.pytorch.org/whl/cpu"
  priority = "explicit"

  [tool.poetry.dependencies]
  torch = { source = "pytorch-cpu" }
  ```

  Then run `poetry lock`. Report that CPU-only wheels will be used.

### 6. Add the dependency

From the target project directory:

- **Poetry, local path:** `poetry add --editable <absolute_apeiron_path>`
- **Poetry, git:** `poetry add "git+<url>"`
- **pip/uv, local path:** `pip install -e <absolute_apeiron_path>` — for the
  no-GPU case, first run
  `pip install torch --index-url https://download.pytorch.org/whl/cpu`
- **pip/uv, git:** `pip install "apeiron @ git+<url>"`

### 7. Verify and report

- Run the import check from **Success criteria** inside the target environment
  (`poetry run python -c ...` for Poetry).
- On success, report the apeiron source used (path or git URL), the target
  Python version, the package manager the dependency was added to, and the
  compute backend chosen (CUDA or CPU).
- Suggest next steps: `apeiron-explore-examples` to try a bundled demo, or
  `integrate-apeiron` to wire apeiron into an existing training loop.

## Troubleshooting

- **`ModuleNotFoundError: apeiron` after install** — the editable/path link did
  not register; re-run the dependency add from the *target* project directory,
  not the apeiron repository.
- **torch pulls CUDA wheels on a CPU box** — the explicit `pytorch-cpu` source
  from step 5 was not applied before locking; add it and re-lock.
- **Python version conflict** — apeiron pins a narrow CPython range (see step
  3). Point the target environment at a compatible interpreter with
  `poetry env use` rather than changing apeiron's requirement.

## Notes

- This skill is vendored from the apeiron project; see the bundle's
  `ATTRIBUTION.md` for where it is developed.
