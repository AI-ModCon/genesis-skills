# Slurm Accounting Reference

Fair-share, allocation management, and usage reporting.

---

## Checking Your Account and Balance

```bash
# Show your account associations (which accounts you can charge)
sacctmgr show associations user=$USER format=account,partition,qos,grptres,maxjobs

# Show all accounts you belong to
sacctmgr show user $USER withassoc

# Show QOS definitions (time limits, priority factors, resource caps)
sacctmgr show qos format=name,priority,maxwall,maxjobspu,grptresrunmins
```

---

## `sacctmgr` — Account Manager

`sacctmgr` reads and writes the Slurm accounting database. Most operations are read-only for regular users.

### Useful Read Operations

```bash
# List all accounts
sacctmgr list accounts

# Details for a specific account
sacctmgr show account myproject

# Show account hierarchy (parent/child tree)
sacctmgr show associations tree

# Show resource limits for your account
sacctmgr show associations user=$USER format=account,maxcpumin,maxjobs,grptres

# List available QOS tiers
sacctmgr show qos
```

### Understanding Association Fields

| Field | Meaning |
|-------|---------|
| `Account` | Account name |
| `MaxCPUMins` | Max CPU-minutes this account can consume |
| `MaxJobs` | Max concurrent jobs |
| `MaxNodes` | Max nodes per job |
| `GrpTRES` | Group resource limits (CPUs, GPUs, etc.) |
| `GrpTRESRunMins` | Running CPU-minute limit |
| `QOS` | Allowed QOS tiers |
| `Fairshare` | Relative share weight vs. sibling accounts |

---

## `sshare` — Fair-Share Tree

Fair-share affects job priority: accounts that have used more than their share get lower priority.

```bash
# Show fair-share for all users in your account
sshare -A myproject

# Show your personal fair-share
sshare -u $USER

# Full tree with usage details
sshare -l
```

### Reading `sshare` Output

| Column | Meaning |
|--------|---------|
| `RawShares` | Configured share weight |
| `NormShares` | Normalized share (fraction of total) |
| `RawUsage` | CPU-seconds consumed |
| `EffectvUsage` | Effective usage (decays over time) |
| `FairShare` | Score 0–1; <0.5 means overused, >0.5 means underused |

A `FairShare` score near 0 means your account has consumed much more than its share and will have low priority until decay brings it back up.

---

## `sreport` — Usage Reports

```bash
# Cluster utilization by account, last 30 days
sreport cluster AccountUtilizationByUser \
  Start=$(date -d '30 days ago' +%Y-%m-%d) End=now

# Top users by CPU hours
sreport user TopUsage Start=2025-01-01 End=2025-04-01

# Top accounts by CPU hours
sreport account TopUsage Start=2025-01-01 End=2025-04-01

# Your account's usage vs. allocation
sreport cluster AccountUtilizationByUser Account=myproject \
  Start=2025-01-01 End=2025-04-01

# Utilization by partition
sreport cluster Utilization Start=2025-01-01 End=2025-04-01

# Job count by account
sreport job SizesByAccount Start=2025-01-01 End=2025-04-01
```

---

## Estimating Job Cost Before Submitting

Many HPC facilities charge in "service units" (SUs), typically:

```
SUs = nodes × walltime_hours × charge_factor
```

where `charge_factor` depends on node type and QOS tier (e.g., GPU nodes often cost more than CPU nodes).

To estimate before submitting:
1. Know your node type and QOS charge factor (check facility docs or `sacctmgr show qos`)
2. Multiply: `SUs = nodes × hours × factor`
3. Compare against remaining balance before submitting large jobs

---

## Priority Factors

Slurm uses a multi-factor priority model. Run `sprio` to see all factors for your queued jobs:

```bash
sprio -j 12345
sprio -u $USER
```

| Factor | Description |
|--------|-------------|
| `FairShare` | Based on historic usage vs. shares |
| `Age` | Jobs waiting longer get higher priority |
| `JobSize` | Configured to favor large or small jobs |
| `Partition` | Per-partition weight |
| `QOS` | QOS-level priority multiplier |
| `NICE` | User-adjustable penalty (`sbatch --nice=N`) |

To see weights:
```bash
scontrol show config | grep PriorityWeight
```

---

## `sacct` for Billing

```bash
# Show billing units for completed jobs
sacct -j 12345 --format=JobID,AllocTRES,Elapsed,CPUTimeRAW

# AllocTRES shows resources charged: cpu=N,mem=XM,node=N,gres/gpu=N

# Compute approximate SU cost (CPU-hours)
sacct -j 12345 --format=CPUTimeRAW | awk 'NR>2{print $1/3600 " CPU-hours"}'
```

---

## Troubleshooting Allocation Issues

**Job rejected with "Invalid account":**
```bash
sacctmgr show user $USER withassoc   # verify account names
# Use exact account name as shown
```

**Job rejected with "Unable to allocate resources: Invalid qos specification":**
```bash
sacctmgr show associations user=$USER format=account,qos
# Use only QOS tiers listed in your association
```

**Allocation exhausted (zero balance):**
```bash
# Check with your facility's portal or:
sreport cluster AccountUtilizationByUser Account=myproject Start=year-start
# Contact your project PI or facility help desk to request a supplement
```
