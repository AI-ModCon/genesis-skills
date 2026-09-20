# Getting Started

Genesis Skills is a collection of reusable Agent Skills for scientific discovery and engineering workflows.
There is nothing to compile at the repository root.

## Clone The Repo

```bash
git clone https://github.com/AI-ModCon/genesis-skills.git
cd genesis-skills
```

## Use The Skills Catalog

The repository organizes skills under `skills/<domain>/<skill>/`.
Most agent clients expect each skill to be a direct child of a configured skills directory, so you can either flatten the catalog with the repository tooling or expose the bundled `skill-search` helper.

### Option 1: Flatten Skills

Use the repository's `unpack.sh` helper to copy or symlink skills into your agent's skills directory.

```bash
export SKILLS_DIR="$HOME/.agents/skills"
./unpack.sh --target "$SKILLS_DIR" --mode copy
```

### Option 2: Use `skill-search`

The `skill-search` helper can expose the catalog through a single symlink:

```bash
mkdir -p "$SKILLS_DIR"
ln -s "$PWD/skill-search" "$SKILLS_DIR/skill-search"
```

It discovers the catalog from a sibling `skills/` directory by default, or you can point it at another root with `--central-root` or the `SKILL_SEARCH_CENTRAL_ROOT` environment variable.

## Next Steps

- Read the root `README.md` for the full project overview.
- See `CONTRIBUTING.md` for contribution guidelines and issue reporting.
- See `skill-search/README.md` for details on the catalog helper and its JSON output.
- See `Makefile` for the local lint and test commands (`make lint`, `make test`, and `make test-cov`).
- See `skill-search/search_example/requirements.txt` if you want to run the demo example.
