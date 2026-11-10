# Attribution

**Author:** David Radice (Penn State)

Licensed Apache-2.0 as part of this subtree - see [LICENSE](LICENSE).

Skills included:
- `athenak` — Build, configure, run, and analyze AthenaK (GR)(M)HD, radiation, particle, and numerical-relativity simulations; reads and plots output with plot-tools (`athplot`) and AthenaK `vis/python`

## Sources

The `athenak` skill (written 2026-11) is paraphrased from, and checked against,
the following upstream sources:

- **AthenaK** (https://github.com/IAS-Astrophysics/athenak, BSD-3-Clause),
  `main` at commit `c5a0d7f9155a70149931bf0be5a4ffb673f2532a` (2026-09-11):
  source code, shipped input files, `vis/python`, README, and the project wiki.
  Paper: J. M. Stone, P. D. Mullen, D. Fielding, P. Grete, M. Guo, P. Kempski,
  E. R. Most, C. J. White, and G. N. Wong, *AthenaK: A Performance-Portable
  Version of the Athena++ AMR Framework*, arXiv:2409.16053 (2024).
- **plot-tools / `athplot`** (https://github.com/jfields7/plot-tools,
  GPL-3.0, author Jacob Fields), `main` at commit
  `f29d3e6754696b9b1f2ea764e4455283fd230437` (2026-09-30). The skill documents
  and invokes this package; it does not include or redistribute any of its
  code. The example snippets in the skill are original and only call its
  public API.
- **Kokkos** documentation (https://kokkos.org) for backend and architecture
  CMake options.

The skill also links to the AthenaK user documentation
(https://ias-astrophysics.github.io/athenak-docs/, source
https://github.com/IAS-Astrophysics/athenak-docs) as further reading. No
content was taken from it, and that repository declares no license.

Content is paraphrased from the sources above. Adapted snippets:
- `athenak/assets/minimal_hydro.athinput` and the annotated example in
  `athenak/references/input-format.md` are adapted from AthenaK
  `inputs/hydro/sod.athinput` (BSD-3-Clause): comments added, end time
  shortened, unused keys removed, and a restart output block added.
- The `<mesh_refinement>` / `<amr_criterion>` example in
  `athenak/references/input-format.md` is abridged from AthenaK
  `inputs/hydro/blast_hydro_amr.athinput` (BSD-3-Clause).

The adapted AthenaK snippets are used under the BSD 3-Clause License,
Copyright (c) 2020, Institute for Advanced Study / High-Performance Computing
/ jmstone / Athena-Parthenon. All rights reserved. The full license text and
disclaimer are in [THIRD_PARTY_LICENSE_ATHENAK.txt](THIRD_PARTY_LICENSE_ATHENAK.txt).

The helper scripts (`athenak/scripts/athinput_tool.py`,
`athenak/scripts/hst_summary.py`) are original. They follow the file formats
written by AthenaK's `src/parameter_input.cpp` and `src/outputs/history.cpp`
but contain no AthenaK code. No plot-tools code is included.
