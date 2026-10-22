# Attribution

**Team:** ModCon Base CAF Team

**Author:** Matt Baughman (PPPL)

**Contributors:** Kyle Felker (ANL)

Licensed Apache-2.0 as part of this subtree - see [LICENSE](LICENSE).

Skills included:
- `aurora` — ALCF Aurora (PBS, Intel Ponte Vecchio GPUs, oneAPI/SYCL, DAOS/Lustre flare storage)
- `frontier` — OLCF Frontier (Slurm, AMD MI250X GPUs with ROCm/HIP, Cray programming environment)
- `pbs` — PBS/OpenPBS batch job scheduling on any PBS cluster
- `perlmutter` — NERSC Perlmutter (Slurm, CPU vs GPU nodes, QOS tiers, NERSC allocations)
- `slurm` — Slurm batch job scheduling on any Slurm cluster

## Sources

The `aurora` skill (revised 2026-10) is derived from the ALCF user guides,
published at https://docs.alcf.anl.gov/aurora/ from
https://github.com/argonne-lcf/user-guides. Most content is paraphrased; a few
short command examples (CPU binding lists, the simplified
`gpu_tile_compact.sh`, DAOS container options, `ZEX_NUMBER_OF_CCS`, proxy
settings) are adapted from those pages. No explicit license was found in the
upstream repository at the time of inclusion. Queue limits, filesystem names,
module versions, and `mpiexec` behavior were also checked directly on Aurora
on 2026-10-21; where the live system and the guides disagreed, the skill
follows the live system and says so.
