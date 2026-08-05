# PBS Job Control Reference

Monitoring, inspecting, modifying, and troubleshooting PBS jobs.

---

## `qstat` Usage

```bash
# All your jobs
qstat -u $USER

# All running jobs
qstat -r

# All queued/held jobs
qstat -i

# Full detail for one job (most useful for debugging)
qstat -f 12345

# Wide output (don't truncate long fields)
qstat -w

# One-line per job format
qstat -1

# Estimated start times (server must support this)
qstat -T

# Finished jobs (in server history, usually last 7 days)
qstat -xf 12345

# Array job detail
qstat -t 12345             # show all array elements
qstat -Jt 12345            # detailed array info
```

---

## `qstat -f` Key Fields

When debugging a job, `qstat -f <jobid>` shows everything. Key fields:

| Field | Meaning |
|-------|---------|
| `job_state` | Current state (Q/R/H/E/F) |
| `Hold_Types` | Who placed the hold: u=user, o=operator, s=system |
| `queue` | Queue the job is in |
| `Resource_List.select` | What was requested |
| `resources_used.*` | Actual resources consumed (while running) |
| `Exit_status` | Exit code (non-zero = failure) |
| `comment` | Scheduler comment explaining why job is waiting |
| `Checkpoint` | Checkpoint policy |
| `Error_Path` | Stderr file location |
| `Output_Path` | Stdout file location |
| `euser` | Effective user |
| `egroup` | Effective group |
| `Variable_List` | Environment variables exported to job |
| `start_time` | When job started |
| `etime` | Time job became eligible to run |
| `qtime` | Time job was queued |

---

## Node Status (`pbsnodes`)

```bash
# All nodes and their state
pbsnodes -a

# Specific node
pbsnodes node001

# Only nodes in a particular state
pbsnodes -l             # only offline/down nodes
pbsnodes -s             # summary by state

# JSON output (parseable)
pbsnodes -F json
```

### Node State Values

| State | Meaning |
|-------|---------|
| `free` | Available for jobs |
| `job-busy` | Running jobs (all CPUs busy) |
| `job-exclusive` | Running an exclusive job |
| `down` | Unresponsive / hardware issue |
| `offline` | Administratively taken offline |
| `drained` | Being drained (no new jobs) |
| `stale` | `pbs_mom` hasn't communicated recently |
| `resv-exclusive` | Reserved for a reservation |

---

## Queue Information

```bash
# List all queues and limits
qstat -Q

# Full detail for a queue
qstat -Qf workq

# Server properties
qmgr -c "print server"   # admin only; shows all server settings
```

---

## Modifying Pending Jobs (`qalter`)

Only certain attributes can be changed after submission, and only while the job is in Q or H state.

```bash
# Extend walltime (often restricted; depends on site policy)
qalter -l walltime=8:00:00 12345

# Change memory request
qalter -l select=1:ncpus=32:mem=128gb 12345

# Change queue
qalter -q bigqueue 12345

# Change account
qalter -A differentproject 12345

# Change email
qalter -M new@email.com 12345

# Make job not rerunnable
qalter -r n 12345
```

---

## Troubleshooting

### Job stuck in Q

```bash
# Check the comment field
qstat -f 12345 | grep comment

# Common reasons:
# - "Not Running: Job's resources not available" → cluster full, wait
# - "Job is held" → check Hold_Types field
# - Dependency not satisfied → check -W depend= setting
```

### Job immediately fails (state E or F)

```bash
# Check exit status
qstat -xf 12345 | grep Exit_status

# Read stderr
cat <jobname>.e12345        # default stderr location (in $PBS_O_WORKDIR)
# Or check Output_Path/Error_Path in qstat -f output

# Common causes:
# - Missing module or binary (check module load commands)
# - Wrong working directory (always cd $PBS_O_WORKDIR)
# - Missing filesystems declaration (Aurora-specific)
# - OOM kill → job exits with signal 9
```

### Job output files not found

Default file locations when `-o`/`-e` not specified:
- `<jobname>.o<jobid_number>` — stdout
- `<jobname>.e<jobid_number>` — stderr

These are placed in `$PBS_O_WORKDIR` by default. Check with:
```bash
qstat -f 12345 | grep -E "Output_Path|Error_Path"
```

For finished jobs, check the paths shown in `qstat -xf 12345`.

### OOM (out of memory)

```bash
# Check resources used
qstat -xf 12345 | grep resources_used.mem

# Fix: increase mem in -l select
qalter -l select=1:ncpus=32:mem=128gb 12345
# (only if job is still pending)
```

### Job dependency never satisfied

```bash
qstat -f 12345 | grep depend

# If parent job failed, the dependency type matters:
# afterok  → will NEVER run if parent failed
# afterany → will run regardless
# afternotok → runs ONLY if parent failed
```

---

## Useful One-Liners

```bash
# Count your jobs by state
qstat -u $USER | awk 'NR>5{print $5}' | sort | uniq -c

# Get node list for a running job
qstat -f 12345 | grep exec_host

# Get actual elapsed time
qstat -f 12345 | grep resources_used.walltime

# Check if your job is in the right queue
qstat -f 12345 | grep "queue ="

# All job IDs currently running under your user
qstat -u $USER -r | awk 'NR>5{print $1}' | cut -d. -f1
```
