# Frontier Storage Reference

---

## Filesystem Overview

| Filesystem | Variable | Path | Quota | Purge | Use for |
|-----------|----------|------|-------|-------|---------|
| Home (NFS) | `$HOME` | `/ccs/home/<user>` | 50 GB | None | Code, configs |
| Member work (Lustre) | `$MEMBERWORK` | `/lustre/orion/<proj>/scratch/<user>` | 50 TB | **90-day auto-purge** | Primary job I/O |
| Project work (Lustre) | `$PROJWORK` | `/lustre/orion/<proj>/proj-shared/` | varies | None | Shared project data |
| World work (Lustre) | `$WORLDWORK` | `/lustre/orion/<proj>/world-shared/` | varies | None | Publicly accessible within OLCF |
| NVMe burst buffer | — | `/mnt/bb/<user>` | ~3.84 TB | Job lifetime | Fast local NVMe I/O |
| Kronos (tape archive) | — | `/nl/kronos/olcf/<proj>/` | 200 TB/proj | None | Long-term archival |

---

## `$MEMBERWORK` Auto-Purge Policy

> **Files in `$MEMBERWORK` not accessed for 90 days are permanently and automatically deleted without warning.**

Check for files approaching the purge threshold:
```bash
# Find files not accessed in 80+ days
lfs find $MEMBERWORK --atime +80 -maxdepth 3 -type f

# Reset access time (delays purge timer)
touch "$MEMBERWORK/important_file.h5"

# Better: archive to Kronos or copy to $PROJWORK before files age out
htar -cf /nl/kronos/olcf/myproject/run001.tar -C $MEMBERWORK/run001 .
```

---

## Checking Quotas

```bash
# Check your $MEMBERWORK quota
lfs quota -u $USER /lustre/orion

# Check project workspace quota
lfs quota -g <project_group> /lustre/orion

# Home directory usage
du -sh $HOME

# Check burst buffer (if in a job with -C nvme)
df -h /mnt/bb/$USER
```

---

## Lustre Striping on Orion

Proper Lustre striping improves parallel I/O bandwidth on `$MEMBERWORK`, `$PROJWORK`, and `$WORLDWORK`.

```bash
# Check current stripe settings
lfs getstripe $MEMBERWORK/myoutputdir/

# Set striping on a directory before writing
lfs setstripe -c 8  $MEMBERWORK/small_files/    # small files, fewer OSTs
lfs setstripe -c 32 $MEMBERWORK/large_files/    # large parallel output
lfs setstripe -c -1 $MEMBERWORK/max_stripe/     # all available OSTs

# Set stripe size (default 1 MB; increase for large sequential writes)
lfs setstripe -c 16 -S 4m $MEMBERWORK/big_output/

# Check Orion OST count
lfs df /lustre/orion | grep OST | wc -l
```

### Striping Rules of Thumb

| File size | Recommended stripe count |
|-----------|------------------------|
| < 1 GB | 1–4 |
| 1–10 GB | 8–16 |
| 10–100 GB | 16–64 |
| > 100 GB | `-c -1` (max) |

---

## NVMe Burst Buffer (`/mnt/bb/<user>`)

Each Frontier node has 2× 1.92 TB NVMe SSDs. Request with `#SBATCH -C nvme`.

```bash
NVME="$MEMBERWORK/bb/$USER"    # or simply /mnt/bb/$USER

# Stage data in at job start
cp "$MEMBERWORK/input.h5" "$NVME/"

# Use fast NVMe for I/O during the job
./my_app --input "$NVME/input.h5" --output "$NVME/result.h5"

# Stage results out before job ends (NVMe is wiped after job)
cp "$NVME/result.h5" "$MEMBERWORK/results/"
```

The burst buffer is particularly effective for:
- Many small random reads (avoids Lustre metadata overhead)
- Checkpoint/restart files written and read repeatedly
- Pre-staging input datasets consumed many times per job

---

## `$PROJWORK` and `$WORLDWORK`

```bash
# Project-shared directory (all project members can read/write)
ls $PROJWORK                     # /lustre/orion/<proj>/proj-shared/

# World-shared directory (readable by all OLCF users)
ls $WORLDWORK                    # /lustre/orion/<proj>/world-shared/

# Typical layout
$PROJWORK/
├── software/                    # shared compiled software
├── datasets/                    # shared input data
└── results/                     # team results (not auto-purged)
```

Use `$PROJWORK` for data shared within your team and `$MEMBERWORK` for per-user job I/O.

---

## Kronos Tape Archive

Kronos is OLCF's nearline archival system. Use it for data you want to keep long-term.

```bash
# htar: create a tape archive of a directory
htar -cf /nl/kronos/olcf/myproject/run001.tar -C $MEMBERWORK/run001 .

# htar: list contents of an archive
htar -tf /nl/kronos/olcf/myproject/run001.tar

# htar: extract from archive
htar -xf /nl/kronos/olcf/myproject/run001.tar -C /target/directory

# hsi: interactive tape session
hsi
# Inside hsi:
# ls /nl/kronos/olcf/myproject/
# put localfile remotefile
# get remotefile localfile
# mkdir mydir
```

---

## Data Transfer (Between Systems)

### Globus (Recommended)

```bash
# OLCF Globus endpoint: "OLCF DTN (Globus 5)"
# Find endpoint ID at: app.globus.org or ask OLCF help desk

globus transfer \
    <source_endpoint>:<source_path> \
    <olcf_endpoint>:$MEMBERWORK/incoming/ \
    --recursive
```

### DTN Nodes (for scp/rsync)

```bash
# Transfer to Frontier via DTN (Data Transfer Nodes)
rsync -avz --progress local_data/ \
    <username>@dtn.olcf.ornl.gov:$MEMBERWORK/incoming/

scp large_file.tar.gz \
    <username>@dtn.olcf.ornl.gov:$MEMBERWORK/
```

---

## Best Practices

1. **Write job output to `$MEMBERWORK`**, never to `$HOME` (too small).
2. **Archive to Kronos** before `$MEMBERWORK` files hit the 90-day mark.
3. **Copy shared datasets to `$PROJWORK`** to avoid each user staging the same data.
4. **Use NVMe** (`-C nvme`) for jobs with intensive checkpoint I/O or small-file access patterns.
5. **Set Lustre striping** on output directories before parallel writes.
6. **Use Globus** for large data transfers between Frontier and other facilities.
7. **Check quotas** (`lfs quota -u $USER /lustre/orion`) before submitting large jobs.
