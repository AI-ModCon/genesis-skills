# PBS Resource Specification Reference

Comprehensive reference for the `-l select=` syntax and related resource directives.

---

## The `select` Statement

The `select` statement describes resource "chunks" (usually nodes) and how many of each to request.

### Grammar

```
-l select=<N>:<property>=<value>:<property>=<value>:...
```

Where `<N>` is the number of chunks. Chunks are scheduled as atomic units — if you request `select=4`, PBS guarantees 4 chunks with the specified properties.

### Common Properties

| Property | Type | Description |
|----------|------|-------------|
| `ncpus` | integer | Logical CPUs (cores or hardware threads) per chunk |
| `mem` | size | Memory per chunk (e.g., `32gb`, `512mb`) |
| `ngpus` | integer | GPUs per chunk |
| `gpu_type` | string | GPU model (site-specific, e.g., `A100`, `V100`) |
| `mpiprocs` | integer | MPI ranks to place per chunk |
| `ompthreads` | integer | OpenMP threads per MPI rank |
| `arch` | string | CPU architecture (site-specific) |
| `host` | string | Specific hostname |
| `accelerator` | boolean | `true` to require any accelerator |
| `scratch` | size | Local scratch space per chunk |
| `interconnect` | string | Network type (site-specific) |

### Examples

```bash
# Minimum: 1 node, 1 CPU
#PBS -l select=1:ncpus=1

# Single node, 32 cores, 64 GB RAM
#PBS -l select=1:ncpus=32:mem=64gb

# 8 nodes, 128 cores each, 512 GB RAM each
#PBS -l select=8:ncpus=128:mem=512gb

# 4 nodes with 2 GPUs each
#PBS -l select=4:ncpus=64:ngpus=2:mem=256gb

# Hybrid: 4 MPI ranks per node, 16 OpenMP threads each, 64 cores total per node
#PBS -l select=4:ncpus=64:mpiprocs=4:ompthreads=16:mem=256gb

# Request specific GPU type (site-dependent token)
#PBS -l select=2:ncpus=32:ngpus=4:gpu_type=A100:mem=128gb

# Request fast local scratch
#PBS -l select=1:ncpus=32:mem=64gb:scratch=100gb
```

---

## `mpiprocs` and `ompthreads`

These properties control how PBS informs MPI libraries about the layout:

- `mpiprocs` = MPI ranks PBS will launch per chunk
- `ompthreads` = OpenMP threads per MPI rank

```bash
# 2 nodes, 4 MPI ranks each, 8 OpenMP threads each = 64 threads total/node
#PBS -l select=2:ncpus=32:mpiprocs=4:ompthreads=8:mem=64gb
```

`ncpus` should equal `mpiprocs × ompthreads` to fully use the node.

---

## The `place` Directive

Controls how chunks are distributed across physical nodes:

```bash
#PBS -l place=<arrangement>[:<sharing>]
```

### Arrangement Options

| Value | Meaning |
|-------|---------|
| `free` | PBS chooses placement (default) |
| `pack` | Fill nodes as full as possible (minimize node count) |
| `scatter` | One chunk per node (maximize spread) |
| `vscatter` | One chunk per NUMA domain |
| `group=<property>` | Group chunks by a node property |

### Sharing Options

| Value | Meaning |
|-------|---------|
| `excl` | Job has exclusive use of all nodes |
| `shared` | Nodes may be shared with other jobs (default) |
| `exclhost` | Exclusive use of each host, but chunks may share within |

### Common Combinations

```bash
# One chunk per node, exclusive (typical production HPC setup)
#PBS -l place=scatter:excl

# Pack onto fewest nodes, sharing allowed (efficient for small jobs)
#PBS -l place=pack:shared

# Spread out, no sharing
#PBS -l place=scatter:excl

# Let PBS decide (most flexible)
#PBS -l place=free
```

---

## Walltime Format

```
HH:MM:SS         00:30:00  = 30 minutes
                 02:00:00  = 2 hours
                 23:59:59  = nearly 24 hours
D:HH:MM:SS       1:12:00:00 = 36 hours (some PBS versions)
```

Walltime limits are enforced: the job is killed when walltime is reached.

---

## Other `-l` Resources

```bash
# Set eligible start time (deferred submission)
#PBS -a 202501151400        # eligible at 2:00 PM on Jan 15, 2025
                             # format: CCYYMMDDhhmm[.ss]

# Job group (for priority grouping, site-specific)
#PBS -l group=mygroupname

# Minimum/maximum node count (optimization window)
#PBS -l select=4-8:ncpus=32:mem=64gb   # 4 to 8 nodes acceptable
```

---

## Environment Variables Set by PBS

PBS sets these inside the job based on the `select` statement:

| Variable | Value |
|----------|-------|
| `$PBS_NP` | Total number of CPUs (sum of ncpus across all chunks) |
| `$PBS_NUM_NODES` | Number of chunks/nodes |
| `$PBS_NODEFILE` | Path to file listing allocated node slots |
| `$OMP_NUM_THREADS` | Set to `ompthreads` value if specified |

Check what you got:
```bash
echo "Nodes: $PBS_NUM_NODES, CPUs: $PBS_NP"
echo "Node list: $(sort -u $PBS_NODEFILE | tr '\n' ' ')"
```

---

## Checking Available Resources

```bash
# Show all nodes with their properties
pbsnodes -a

# Show queues and their limits
qstat -Q -f

# List what resources a specific queue allows
qstat -Qf myqueue | grep -E "resources_max|resources_min|resources_default"
```

---

## Resource Efficiency Tips

1. **Match `ncpus` to your parallelism:** requesting more CPUs than your app uses wastes allocation and delays scheduling.
2. **Estimate memory before running:** use a test run with `qstat -f` → `resources_used.mem` to calibrate.
3. **Use `scatter:excl` for MPI jobs** to avoid NUMA interference from other jobs.
4. **Set walltime 10–20% above expected runtime** — too tight and the job gets killed; too long and it sits in the queue longer.
5. **`mpiprocs × ompthreads = ncpus`** — always verify this equation to avoid over- or under-subscribing cores.
