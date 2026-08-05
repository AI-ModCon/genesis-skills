# Slurm Job Control Reference

Monitoring, inspecting, modifying, and troubleshooting Slurm jobs.

---

## `squeue` Format Recipes

```bash
# Default columns
squeue -u $USER

# Wide format with more information
squeue -u $USER -o "%.18i %.9P %.20j %.8u %.8T %.10M %.9l %.6D %R"
#                   jobid  partition  name     user   state  time  timelimit nodes reason

# Show estimated start time for pending jobs
squeue -u $USER --start

# Watch your jobs, refresh every 10 seconds
watch -n 10 squeue -u $USER

# Show one line per array task
squeue -r -j 12345

# Sort by time remaining (ascending)
squeue -u $USER --sort=-L
```

### Column Format Codes

| Code | Field |
|------|-------|
| `%i` | Job ID |
| `%P` | Partition |
| `%j` | Job name |
| `%u` | User |
| `%T` | State |
| `%M` | Elapsed time |
| `%l` | Time limit |
| `%D` | Node count |
| `%R` | Reason (for PD) or nodelist (for R) |
| `%C` | CPUs |
| `%m` | Min memory |
| `%b` | GRES (GPUs etc.) |
| `%S` | Expected start time |

---

## Pending Job Reason Codes

| Reason | Meaning | What to do |
|--------|---------|-----------|
| `Resources` | Not enough free nodes/CPUs | Wait; normal backlog |
| `Priority` | Higher-priority jobs ahead | Wait; lower-cost QOS may help |
| `QOSMaxJobsPerUserLimit` | Hit per-user job count limit | Cancel some jobs |
| `QOSMaxCpuPerUserLimit` | CPU quota exceeded | Reduce node count or cancel jobs |
| `QOSMaxNodePerJobLimit` | Requested too many nodes for QOS | Use larger QOS tier |
| `ReqNodeNotAvail` | Specific nodes down or reserved | Remove `--nodelist` constraint |
| `Dependency` | Waiting for dependency | Check parent job status |
| `DependencyNeverSatisfied` | Parent job failed | Resubmit chain |
| `BeginTime` | Deferred with `--begin` | Time hasn't arrived yet |
| `AssocGrpCPUMinutesLimit` | Allocation exhausted | Contact project PI |
| `launch failed requeued held` | Node failure on last attempt | `scontrol release <id>` |

---

## `scontrol` Recipes

```bash
# Full job detail (includes pending reason, TRES, bind info)
scontrol show job 12345

# Modify a pending job
scontrol update JobId=12345 TimeLimit=8:00:00     # extend walltime
scontrol update JobId=12345 NumNodes=16           # change node count
scontrol update JobId=12345 Partition=gpu         # move to different partition
scontrol update JobId=12345 Account=otherproject  # change account

# Hold and release
scontrol hold 12345
scontrol release 12345

# Requeue a failed job (reruns it as if newly submitted)
scontrol requeue 12345

# Show partition info (QOS limits, nodes)
scontrol show partition regular

# Show node detail
scontrol show node nid001234

# Show reservations
scontrol show reservations
```

---

## `sacct` — Completed Job Accounting

```bash
# Recent jobs (defaults to today)
sacct -u $USER

# Specific job
sacct -j 12345

# Useful columns for job analysis
sacct -j 12345 \
  --format=JobID,JobName,State,Elapsed,CPUTime,MaxRSS,MaxVMSize,ExitCode,Submit,Start,End

# All jobs in a time range
sacct -u $USER --starttime=2025-01-01 --endtime=2025-03-31 \
  --format=JobID,State,Elapsed,CPUTime

# Only failed jobs
sacct -u $USER --state=FAILED --starttime=today-30days

# Check memory efficiency
sacct -j 12345 --format=JobID,ReqMem,MaxRSS,MaxVMSize
```

### Key `sacct` Fields

| Field | Meaning |
|-------|---------|
| `JobID` | Job ID (includes `.batch` and `.extern` substeps) |
| `State` | Final state |
| `Elapsed` | Wall-clock time used |
| `CPUTime` | Elapsed × CPU count |
| `MaxRSS` | Peak resident memory (batch step) |
| `ExitCode` | Exit code (format: code:signal) |
| `AllocCPUS` | CPUs allocated |
| `AllocNodes` | Nodes allocated |
| `ConsumedEnergy` | Energy used (if sensors present) |

---

## `sinfo` — Cluster Status

```bash
# All partitions and node states
sinfo

# Summary per partition
sinfo -s

# Detailed node list
sinfo -l

# GPU partition only
sinfo -p gpu

# Nodes that are down/drained
sinfo -t down,drained

# Custom format
sinfo -o "%P %a %C %D %G"
# partition, availability, CPUs(A/I/O/T), nodes, GRES
```

### Node State Codes

| State | Meaning |
|-------|---------|
| `idle` | Available |
| `alloc` | Fully allocated |
| `mix` | Partially allocated |
| `down` | Unavailable (hardware/software issue) |
| `drain` | Draining (no new jobs, current jobs finish) |
| `drng` | Actively draining |
| `resv` | In a reservation |
| `comp` | Completing (jobs finishing) |

---

## Troubleshooting

### Job exits immediately (exit code != 0)

```bash
# Check exit code and state
sacct -j 12345 --format=JobID,State,ExitCode

# Read the stderr file
cat myjob_12345.err

# Check if the binary exists and is executable
scontrol show job 12345 | grep Command
```

### Out-of-memory (OOM) kill

The job state will be `OUT_OF_MEMORY` or `FAILED` with signal 9.

```bash
# See how much memory was actually used
sacct -j 12345 --format=JobID,ReqMem,MaxRSS

# Fix: increase --mem or --mem-per-cpu in the script
```

### Job never starts (stuck in PD)

```bash
# See the reason
squeue -j 12345 -o "%R"

# Try simulating a smaller job
scontrol show job 12345 | grep -E "Reason|Priority|EligibleTime"
```

### Node failure mid-job

```bash
# If requeued and held:
scontrol release 12345

# Check which node failed
scontrol show job 12345 | grep NodeList
sinfo -n <nodename>
```

### Diagnosing walltime needs

```bash
# Look at elapsed times for similar past jobs
sacct -u $USER --format=JobName,Elapsed,State | grep my_app_name | head -20
```

---

## `sstat` — Running Job Statistics

For jobs currently running, `sstat` shows live resource usage:

```bash
sstat -j 12345 --format=JobID,AveCPU,MaxRSS,MaxVMSize,NTasks
sstat -j 12345.batch --format=JobID,MaxRSS,MaxDiskRead,MaxDiskWrite
```

Note: `sstat` only works while a job is running; use `sacct` after it completes.
