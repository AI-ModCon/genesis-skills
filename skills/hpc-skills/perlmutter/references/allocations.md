# Perlmutter Allocation and Accounting Reference

---

## Checking Your Allocation Balance

### `iris` Command (NERSC-specific)

The `iris` CLI is the primary tool for checking NERSC allocations from the command line.

```bash
# Summary of all your projects
iris

# CPU and GPU hours: allocated vs. used
iris hours

# Recent job history with SU charges
iris jobs

# Filter by project
iris jobs --project myproject

# Usage by user within a project (PIs and managers)
iris usage --project myproject

# Storage quotas
iris storage
```

### `iris` Web Interface

https://iris.nersc.gov

Key sections:
- **My Account** tab: per-project CPU/GPU hour balances, QOS access, remaining allocation
- **Jobs** tab: searchable job history with SU charges, efficiency metrics
- **Storage** tab: scratch/CFS/HPSS quotas and usage
- **My Projects** tab (PIs): team usage breakdown, per-user charges, time-series plots

---

## Understanding SU Charges

NERSC charges in **NERSC Hours** (NH), which equals CPU-core-hours for CPU nodes and a GPU-node-hours equivalent for GPU nodes.

### Charge Formula

```
Charge (NH) = nodes × wall_hours × charge_factor × QOS_multiplier
```

### Charge Factors (approximate — verify at docs.nersc.gov)

| Node type | Charge factor |
|-----------|--------------|
| CPU node | 1.0 per node-hour |
| GPU node | ~2.5 per node-hour (all 4 A100s) |
| Shared (per GPU) | fraction of GPU node rate |

### QOS Multipliers

| QOS | Multiplier |
|-----|-----------|
| `debug` | 1× (no extra charge) |
| `regular` | 1× |
| `preempt` | 0.25× (GPU) / 0.5× (CPU) |
| `premium` | 2× |
| `shared` | billed per fraction used |

### Big Job Discount
Jobs with **≥128 GPU nodes** or **≥256 CPU nodes** receive a **50% discount** automatically — no special flag needed.

---

## `sacct` on Perlmutter

```bash
# Recent completed jobs
sacct -u $USER --starttime=today --format=JobID,JobName,State,Elapsed,AllocCPUS,AllocNodes,ExitCode

# Specific job detail
sacct -j 12345 --format=JobID,State,Elapsed,MaxRSS,AllocTRES

# All failed jobs this month
sacct -u $USER --starttime=$(date -d '30 days ago' +%Y-%m-%d) --state=FAILED \
  --format=JobID,JobName,State,ExitCode

# Memory usage analysis
sacct -j 12345 --format=JobID,ReqMem,MaxRSS,MaxVMSize
```

---

## Allocation Types at NERSC

| Type | Who can apply | How obtained |
|------|--------------|-------------|
| Startup | New users / small projects | Via NERSC NIM account request |
| Director's Reserve | Special cases | Allocated by NERSC director |
| DOE ERCAP | DOE-funded researchers | Annual ERCAP allocation request |
| ALCC | DOE labs | Via ALCC proposal process |
| INCITE | Open to all | Via INCITE proposal (national competition) |

---

## Requesting a Supplement or New Allocation

1. Log into https://iris.nersc.gov
2. Navigate to **My Projects** → your project → **Request Supplement**
3. Fill in the justification and hours requested
4. Your PI and NERSC facility manager review and approve

For initial allocations, apply through the ERCAP process each fall for the following year.

---

## Adding Users to Your Project

Project PIs and managers can add users via:
- https://iris.nersc.gov → My Projects → Members → Add Member
- Or https://nim.nersc.gov (NERSC Identity Manager)

Users need a NERSC account before they can be added to a project.

---

## Understanding Your `sacctmgr` Associations

```bash
# See which accounts and QOS tiers you have access to
sacctmgr show associations user=$USER format=account,partition,qos,maxjobs

# See your fair-share status
sshare -u $USER

# Check QOS definitions and limits
sacctmgr show qos format=name,priority,maxwall,grptresrunmins,maxjobspu
```

---

## Common Accounting Issues

**"Invalid account" at job submission:**
```bash
sacctmgr show associations user=$USER
# Use the exact account name shown (case-sensitive on some systems)
```

**Job starts but charges wrong project:**
```bash
# Check which account is being charged
sacct -j 12345 --format=JobID,Account
# Resubmit with explicit -A myproject
```

**Allocation shows negative balance:**
- Negative means you've exceeded your allocation for the period
- Contact your PI — they can request a supplement from NERSC
- You can still submit jobs if site policy allows overdraft (check with help desk)
