---
name: pbs
description: >
  PBS/OpenPBS job scheduler for HPC batch job scheduling. Use when submitting
  batch or interactive jobs with qsub, monitoring with qstat, deleting with
  qdel, writing #PBS job scripts, specifying resources with the select/ncpus/
  mem/ngpus syntax, setting walltime, working with job arrays (-t flag),
  setting dependencies with -W depend=, checking job accounting, or
  troubleshooting jobs on any PBS or OpenPBS cluster.
compatibility: Requires access to a PBS cluster (qsub, qstat, qdel, pbsnodes available in PATH).
metadata:
  version: "1.0"
  scheduler: pbs
allowed-tools: Bash(qsub *) Bash(qstat *) Bash(qdel *) Bash(qhold *) Bash(qrls *) Bash(qalter *) Bash(qmove *) Bash(pbsnodes *) Read Write
---

# PBS / OpenPBS Job Scheduler

PBS (Portable Batch System) is widely used at DOE labs (ALCF, etc.) and many academic HPC centers. Jobs are described with `#PBS` directives and submitted via `qsub`.

## Quick Command Reference

| Command | Purpose |
|---------|---------|
| `qsub script.sh` | Submit a batch job script |
| `qsub -I` | Start an interactive job |
| `qstat` | View job queue |
| `qstat -f <id>` | Full job detail |
| `qdel <id>` | Delete/cancel a job |
| `qhold <id>` | Place a user hold on a job |
| `qrls <id>` | Release a held job |
| `qalter <id>` | Modify a pending job |
| `pbsnodes -a` | List all nodes and their state |
| `qstat -Q` | List available queues |

### Job State Codes

| Code | State | Meaning |
|------|-------|---------|
| Q | Queued | Waiting for resources |
| R | Running | Currently executing |
| H | Held | Held by user, operator, or system |
| E | Exiting | Job is finishing/cleaning up |
| C | Completed | Finished (may appear briefly) |
| F | Finished | Job is done (in history) |
| S | Suspended | Temporarily suspended |
| W | Waiting | Waiting for eligible start time (`-a`) |

## Writing Job Scripts

`#PBS` directives must appear before any non-comment executable line.

**Minimal working script:**
```bash
#!/bin/bash
#PBS -N myjob
#PBS -A myproject
#PBS -l select=1:ncpus=32:mem=64gb
#PBS -l walltime=01:00:00
#PBS -o myjob.out
#PBS -e myjob.err
#PBS -q workq

cd $PBS_O_WORKDIR
module load gcc openmpi
mpiexec -n 32 ./my_application
```

### Key `#PBS` Directives

| Directive | Example | Notes |
|-----------|---------|-------|
| `-N` | `myjob` | Job name |
| `-A` | `myproject` | Account/project (often mandatory) |
| `-l select=...` | `2:ncpus=128:mem=256gb` | Resource selection (see below) |
| `-l walltime=` | `02:30:00` | Wall clock limit (`HH:MM:SS`) |
| `-q` | `workq` | Queue/destination |
| `-o` | `job.out` | Stdout path |
| `-e` | `job.err` | Stderr path |
| `-j oe` | — | Merge stdout+stderr into one file |
| `-m abe` | — | Email on abort/begin/end |
| `-M` | `user@host.edu` | Email address |
| `-V` | — | Export all current env vars to job |
| `-v VAR=val` | `NPROCS=8` | Export specific variable |
| `-r n` | — | Job is not rerunnable |
| `-a` | `202501011400` | Eligible start time (`CCYYMMDDhhmm`) |
| `-W depend=` | `afterok:12345` | Job dependency |
| `-t` | `1-100` | Job array (see below) |

### Resource Select Syntax

`-l select=<N>:<property>=<value>:...` where N is the number of "chunks" (typically nodes).

```bash
# 1 node, 16 CPUs, 32 GB RAM
#PBS -l select=1:ncpus=16:mem=32gb

# 4 nodes, 128 CPUs each, 2 GPUs each
#PBS -l select=4:ncpus=128:mem=256gb:ngpus=2

# MPI + OpenMP hybrid (mpiprocs = MPI ranks per chunk)
#PBS -l select=2:ncpus=64:mpiprocs=4:ompthreads=16:mem=128gb

# Request specific node features
#PBS -l select=1:ncpus=32:arch=broadwell
```

`place` directive controls layout:
```bash
#PBS -l place=scatter          # one chunk per node (default)
#PBS -l place=pack             # pack chunks onto fewest nodes
#PBS -l place=excl             # exclusive node access
#PBS -l place=scatter:excl     # one per node, exclusive
```

## Submitting Jobs

```bash
# Batch submission
qsub script.sh

# Override directives at submission
qsub -l select=4 -l walltime=2:00:00 script.sh

# Interactive job (drops into shell on allocated node)
qsub -I -l select=1:ncpus=8 -l walltime=1:00:00 -q debug

# Interactive with environment exported
qsub -I -V -l select=1:ncpus=16:mem=32gb -l walltime=2:00:00
```

## Monitoring Jobs

```bash
# All your jobs
qstat -u $USER

# All running jobs
qstat -r

# All queued/held jobs
qstat -i

# Full detail for one job
qstat -f 12345

# Finished job details (past ~7 days, if server configured)
qstat -xf 12345

# Estimated start times
qstat -T

# List queues and their limits
qstat -Q

# All node states
pbsnodes -a
```

**Default output file locations** (when `-o`/`-e` not specified):
- Stdout: `<jobname>.o<jobid>` in `$PBS_O_WORKDIR`
- Stderr: `<jobname>.e<jobid>` in `$PBS_O_WORKDIR`

Watch a running job's output:
```bash
tail -f myjob.o12345
```

## Cancelling, Holding, and Modifying Jobs

```bash
qdel 12345                    # cancel job
qdel 12345[5]                 # cancel array element 5
qdel -W force 12345           # force delete (if qdel hangs)

qhold 12345                   # place user hold (state → H)
qrls 12345                    # release hold

qalter -l walltime=4:00:00 12345   # extend walltime (if pending)
qalter -l select=8 12345           # change node count (if pending)
```

## Job Arrays

Submit many similar jobs from one `qsub`. Resources apply to **each** array element independently.

```bash
# In the script:
#PBS -t 1-100            # indices 1..100
#PBS -t 1-50:2           # odd indices 1,3,5,...,49
#PBS -t 1-100%10         # max 10 running simultaneously
```

Or at submission: `qsub -t 1-100 script.sh`

Inside the script, use `$PBS_ARRAY_INDEX`:
```bash
INPUT="data/input_${PBS_ARRAY_INDEX}.txt"
mpiexec ./process "$INPUT"
```

Array management:
```bash
qstat -t 12345            # show all elements
qdel 12345[]              # delete entire array
qdel 12345[5]             # delete element 5
```

## Job Dependencies

```bash
# Submit job1, capture ID
JOB1=$(qsub stage1.sh)

# Submit job2 to run only if job1 succeeds
qsub -W depend=afterok:$JOB1 stage2.sh

# Common dependency types:
# afterok:<id>     — start if <id> exits with code 0
# afternotok:<id>  — start if <id> exits with non-zero code
# afterany:<id>    — start regardless of <id> outcome
# before:<id>      — <id> starts only after this job begins
# beforeok:<id>    — <id> starts only if this job succeeds
```

## Common Environment Variables (Inside a Job)

| Variable | Value |
|----------|-------|
| `$PBS_JOBID` | Full job ID (e.g., `12345.server`) |
| `$PBS_JOBNAME` | Job name |
| `$PBS_O_WORKDIR` | Directory where `qsub` was run |
| `$PBS_O_HOST` | Host where `qsub` was run |
| `$PBS_NODEFILE` | File listing allocated nodes (for MPI) |
| `$PBS_NP` | Total number of CPUs/tasks |
| `$PBS_NUM_NODES` | Number of nodes |
| `$PBS_QUEUE` | Queue name |
| `$PBS_ARRAY_INDEX` | Array task index (array jobs only) |
| `$PBS_ARRAY_ID` | Parent array job ID |

**Using `$PBS_NODEFILE` with MPI:**
```bash
mpiexec -hostfile $PBS_NODEFILE -n $PBS_NP ./my_app
# or simply:
mpiexec -n $PBS_NP ./my_app   # if MPI is PBS-aware
```

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
- Monitoring, qstat field glossary, troubleshooting: [references/job-control.md](references/job-control.md)
- Full resource select and place reference: [references/resource-spec.md](references/resource-spec.md)
- Copy-paste templates: [assets/templates/](assets/templates/)
