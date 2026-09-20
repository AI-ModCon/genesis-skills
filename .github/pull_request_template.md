# Pull Request Checklist

Use this checklist for new-skill PRs and any change that affects attribution, licensing, or the repository tree.

## Skill Content

- [ ] I added or updated the skill under `skills/<domain>/<skill>/`.
- [ ] `SKILL.md` stays focused and the supporting files live in the same subtree.
- [ ] Any client-specific syntax is clearly labeled and isolated.

## Attribution and Licensing

- [ ] I added or updated the relevant `ATTRIBUTION.md` or attribution section in the skill subtree.
- [ ] New author names were added in the attribution source file, not only in the root README.
- [ ] I added a subtree `LICENSE` or `LICENSE.txt` when imported content requires it.
- [ ] I updated `NOTICE` if this change adds or changes third-party provenance or licensing notes.

## Repository Docs

- [ ] I updated the root `README.md` repository structure block if the visible tree changed.
- [ ] I confirmed the root README contributor list still matches the attribution sources.
- [ ] If I introduced a new top-level skill family or a new attribution format, I updated `tools/repo_inventory.py` and its tests.

## Validation

- [ ] `make verify-new-skill`

If a checkbox does not apply, please explain why in the PR description.
