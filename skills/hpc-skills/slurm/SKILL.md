---
name: slurm
description: >
  Slurm workload manager for HPC batch job scheduling. Use when submitting
  batch or interactive jobs with sbatch/salloc/srun, monitoring with
  squeue/sacct/scontrol, cancelling with scancel, writing #SBATCH job scripts,
  working with job arrays, setting job dependencies, checking fair-share
  accounting with sacctmgr/sreport, or troubleshooting failed jobs on any
  Slurm cluster.
compatibility: Requires access to a Slurm cluster (sbatch, squeue, sacct, sinfo available in PATH).
metadata:
  version: "1.0"
  scheduler: slurm
allowed-tools: Bash(sbatch *) Bash(squeue *) Bash(scancel *) Bash(sinfo *) Bash(sacct *) Bash(salloc *) Bash(srun *) Bash(scontrol *) Bash(sacctmgr *) Bash(sreport *) Read Write
---

# Slurm Workload Manager

Slurm is the dominant HPC batch scheduler. Jobs are submitted to queues (partitions), allocated nodes, and run with full or partial node access.

## Quick Command Reference

| Command | Purpose |
|---------|---------|
| `sbatch script.sh` | Submit a batch job script |
| `salloc` | Allocate nodes for an interactive session |
| `srun` | Run a parallel job step (inside or outside a batch job) |
| `squeue` | View pending and running jobs |
| `scontrol show job <id>` | Detailed job info |
| `scancel <id>` | Cancel a job |
| `scontrol hold/release <id>` | Hold or release a pending job |
| `sinfo` | Cluster partition and node status |
| `sacct` | Query completed job accounting records |
| `sacctmgr` | Manage accounts, QOS, and allocations |

### Job State Codes

| Code | State | Meaning |
|------|-------|---------|
| PD | PENDING | Waiting for resources |
| R | RUNNING | Currently executing |
| CG | COMPLETING | Cleaning up after execution |
| CD | COMPLETED | Finished with exit code 0 |
| CA | CANCELLED | Cancelled by user or admin |
| F | FAILED | Non-zero exit code |
| TO | TIMEOUT | Exceeded time limit |
| OOM | OUT_OF_MEMORY | Killed by memory manager |
| PR | PREEMPTED | Preempted by higher-priority job |

## Writing Job Scripts

Directives go at the top of the script as `#SBATCH` comments before any executable line.

**Minimal working script:**
```bash
#!/bin/bash
#SBATCH --job-name=myjob
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=32
#SBATCH --time=01:00:00
#SBATCH --account=myproject
#SBATCH --output=myjob_%j.out
#SBATCH --error=myjob_%j.err

module load gcc openmpi
srun ./my_application
```

### Key `#SBATCH` Directives

| Directive | Example | Notes |
|-----------|---------|-------|
| `--job-name` | `myjob` | Shown in squeue |
| `--nodes` / `-N` | `4` | Number of nodes |
| `--ntasks-per-node` | `128` | MPI ranks per node |
| `--cpus-per-task` / `-c` | `4` | Threads per MPI rank |
| `--time` / `-t` | `2-00:00:00` | `D-HH:MM:SS` or `HH:MM:SS` |
| `--partition` / `-p` | `gpu` | Queue to use |
| `--account` / `-A` | `myproject` | Allocation to charge |
| `--output` / `-o` | `job_%j.out` | Stdout path |
| `--error` / `-e` | `job_%j.err` | Stderr path |
| `--gres` | `gpu:4` | Generic resources (GPUs) |
| `--mem` | `64G` | Memory per node |
| `--mem-per-cpu` | `4G` | Memory per CPU core |
| `--exclusive` | — | Reserve entire node(s) |
| `--dependency` | `afterok:12345` | Wait for another job |
| `--array` | `0-99` | Submit job array |
| `--mail-type` | `END,FAIL` | Email notifications |
| `--mail-user` | `user@host` | Email address |

### Output Filename Tokens

| Token | Meaning |
|-------|---------|
| `%j` | Job ID |
| `%A` | Array parent job ID |
| `%a` | Array task index |
| `%x` | Job name |
| `%N` | First node name |

## Submitting Jobs

```bash
# Batch submission
sbatch script.sh

# Override directives at submission
sbatch --nodes=8 --time=4:00:00 script.sh

# Interactive allocation (drops into a shell on allocated node)
salloc --nodes=2 --time=1:00:00 --partition=debug
srun ./my_app          # run within the allocation
exit                   # release allocation

# One-off parallel command (creates its own allocation)
srun --nodes=1 --ntasks=4 ./my_app
```

## Monitoring Jobs

```bash
# Your jobs
squeue -u $USER

# All jobs, long format
squeue -l

# Specific job
squeue -j 12345

# Estimated start times for pending jobs
squeue --start -u $USER

# Full detail (reason for pending, TRES, etc.)
scontrol show job 12345

# Live updates every 5 seconds
watch -n5 squeue -u $USER
```

**Reading output files:** Slurm writes stdout/stderr when the job finishes (or continuously if `--output` is to a path). Watch a running job's output:
```bash
tail -f myjob_12345.out
```

**After job completes:**
```bash
sacct -j 12345 --format=JobID,State,Elapsed,MaxRSS,ExitCode
```

## Cancelling and Holding Jobs

```bash
scancel 12345                      # cancel by job ID
scancel 12345_5                    # cancel one array element
scancel -u $USER --state=PENDING   # cancel all your pending jobs
scancel -n myjob                   # cancel by name

scontrol hold 12345                # hold a pending job
scontrol release 12345             # release held job
```

## Job Arrays

Run many similar jobs from one submission. Each element gets a unique `SLURM_ARRAY_TASK_ID`.

```bash
#SBATCH --array=0-99             # indices 0..99
#SBATCH --array=1-50:2           # odd indices 1,3,5,...,49
#SBATCH --array=0-999%20         # up to 20 running at once
#SBATCH --output=job_%A_%a.out   # %A=parent ID, %a=task index
```

Inside the script, use `$SLURM_ARRAY_TASK_ID` to select input:
```bash
INPUT="data/input_${SLURM_ARRAY_TASK_ID}.txt"
srun ./process "$INPUT"
```

Array management:
```bash
squeue -r -j 36           # show all elements
scancel 36                # cancel entire array
scancel 36_[1-5]          # cancel elements 1–5
```

## Job Dependencies

Chain jobs so they start only when a predecessor finishes:

```bash
JOB1=$(sbatch stage1.sh | awk '{print $4}')
sbatch --dependency=afterok:$JOB1 stage2.sh

# Common dependency types:
# afterok:<id>    — start only if <id> succeeds
# afterany:<id>   — start regardless of <id> outcome
# afternotok:<id> — start only if <id> fails
# singleton       — only one job with this name runs at a time
```

## Common Environment Variables (Inside a Job)

| Variable | Value |
|----------|-------|
| `$SLURM_JOB_ID` | Job ID |
| `$SLURM_NODELIST` | List of allocated nodes |
| `$SLURM_NTASKS` | Total number of tasks |
| `$SLURM_CPUS_PER_TASK` | CPUs per task |
| `$SLURM_SUBMIT_DIR` | Directory where `sbatch` was run |
| `$SLURM_ARRAY_JOB_ID` | Parent array job ID |
| `$SLURM_ARRAY_TASK_ID` | This element's index |

## Module System

```bash
module avail              # list available modules
module spider <pkg>       # search for a package
module load gcc/12 openmpi/4.1
module list               # show loaded modules
module purge              # unload everything
```

Always load modules inside the job script, not just in your login shell.

## Additional Resources

- Annotated job script examples: [references/job-scripts.md](references/job-scripts.md)
- Monitoring, troubleshooting, scontrol recipes: [references/job-control.md](references/job-control.md)
- Accounting, fairshare, allocation reporting: [references/accounting.md](references/accounting.md)
- Copy-paste templates: [assets/templates/](assets/templates/)
