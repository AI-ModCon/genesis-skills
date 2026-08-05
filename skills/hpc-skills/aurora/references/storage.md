# Aurora Storage Reference

---

## Filesystem Overview

| Name | Token | Path | Capacity | Purge | Notes |
|------|-------|------|----------|-------|-------|
| Home | `home` | `/home/<user>` | 100 GB/user | None | Code, configs; must declare |
| Flare (Lustre) | `flare` | `/lus/flare/projects/<proj>/` | large | None | Primary project storage |
| Grand | `grand` | `/grand/projects/<proj>/` | — | None | Cross-facility storage |
| Eagle | `eagle` | `/eagle/projects/<proj>/` | — | None | Cross-facility storage |
| DAOS | varies | via `dfuse` or daos API | 260 PB | None | Ultra-high-performance |

> **Mandatory:** ALL filesystems your job accesses must be declared in `-l filesystems=<tokens>`. Omitting a token causes a job failure at startup.

---

## Flare Lustre Filesystem

Flare is the primary Lustre filesystem for Aurora job I/O.

```bash
# Check your flare quota
lfs quota -u $USER /lus/flare

# Check project quota
lfs quota -g <project_group> /lus/flare

# View stripe settings on a file or directory
lfs getstripe /lus/flare/projects/myproject/

# Set striping for large parallel output
lfs setstripe -c 32 /lus/flare/projects/myproject/output/
```

### Striping Guidelines for Flare

| File size | Recommended stripe count (`-c`) |
|-----------|--------------------------------|
| < 1 GB | 1–4 |
| 1–10 GB | 8–16 |
| 10–100 GB | 32–64 |
| > 100 GB | 64 or `-c -1` (all OSTs) |

---

## DAOS Object Storage

DAOS (Distributed Asynchronous Object Store) is Aurora's primary high-performance storage. It provides ~31 TB/s aggregate bandwidth — significantly faster than Lustre for IO-intensive workloads.

### Architecture Concepts

- **Pool**: Top-level administrative container (quotas set here). Managed by facility.
- **Container**: User-created data container within a pool. Can be POSIX, HDF5, or array type.
- **Namespace**: Accessible via DAOS API, HDF5 VOL connector, or POSIX via `dfuse`.

### DAOS CLI Quick Reference

```bash
# Check your pools (facility assigns pools to projects)
daos pool list

# Query pool details and space
daos pool query --pool <pool_label>

# List containers in a pool
daos container list --pool <pool_label>

# Create a POSIX container
daos container create \
    --pool <pool_label> \
    --type POSIX \
    --label mycontainer \
    --properties "rf:0"   # rf=redundancy factor (0=no redundancy, faster)

# Query container info
daos container query --pool <pool_label> --cont mycontainer

# Destroy a container (permanent!)
daos container destroy --pool <pool_label> --cont mycontainer --force
```

### Mounting DAOS as a POSIX Filesystem (`dfuse`)

`dfuse` mounts a DAOS container as a standard POSIX filesystem, allowing normal file operations.

```bash
# Mount
POOL="mypool"
CONT="mycontainer"
MOUNT="/tmp/daos_${PBS_JOBID}"

mkdir -p "$MOUNT"
dfuse --pool "$POOL" --container "$CONT" --mountpoint "$MOUNT" --foreground &
DFUSE_PID=$!
sleep 3   # wait for mount to be ready

# Use normally
ls "$MOUNT"
cp my_data.h5 "$MOUNT/"
./my_app --data "$MOUNT"

# Unmount (do this before job ends)
fusermount3 -u "$MOUNT"
```

> Always unmount `dfuse` before the job ends. Leaving it mounted can cause issues.

### DAOS + HDF5 (Native I/O, No `dfuse`)

For HDF5 workloads, use the DAOS HDF5 VOL connector for direct high-performance I/O:

```bash
module load hdf5-vol-daos  # check exact module name with: module avail | grep daos

export HDF5_PLUGIN_PATH=<path to vol plugin>
export HDF5_VOL_CONNECTOR="daos under_vol=0;under_info={}"
export DAOS_POOL=<pool_uuid>
export DAOS_CONT=<container_uuid>

mpiexec -n 24 -ppn 6 ./my_hdf5_app
```

---

## Data Transfer

### Globus (Recommended for Large Transfers)

Aurora has a Globus endpoint. Use the Globus web app or CLI:

```bash
# Install Globus CLI locally
pip install globus-cli
globus login

# Find Aurora's endpoint UUID in the ALCF user portal, then:
globus transfer \
    <source_endpoint>:<source_path> \
    <aurora_endpoint>:<dest_path> \
    --recursive
```

### SCP / SFTP

For smaller transfers, use the ALCF data transfer nodes:

```bash
# From your workstation:
scp mydata.tar.gz <username>@aurora.alcf.anl.gov:/lus/flare/projects/myproject/
sftp <username>@aurora.alcf.anl.gov
```

---

## Best Practices

1. **Declare all filesystems** in `-l filesystems=` — even `home` if you read files there.
2. **Use DAOS for production I/O** when possible — it's faster than Lustre for parallel workloads.
3. **Use Flare for data persistence** — DAOS containers can be lost if a pool is reset.
4. **Set Lustre striping** on Flare output directories before parallel writes.
5. **Unmount `dfuse`** before your PBS job exits.
6. **Use Globus for large transfers** between Aurora and other facilities.
