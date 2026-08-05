# Perlmutter Storage Reference

---

## Filesystem Overview

| Filesystem | Variable | Path | Quota | Purge | Use for |
|-----------|----------|------|-------|-------|---------|
| Home | `$HOME` | `/global/homes/<l>/<user>` | 40 GB | None | Source code, scripts, configs |
| Scratch | `$SCRATCH` / `$PSCRATCH` | `/pscratch/sd/<l>/<user>` | 20 TB | **8-week auto-purge** | Job input/output |
| Community FS | `$CFS` | `/global/cfs/cdirs/<proj>/` | varies | None | Long-term project data |
| Node-local | `$TMPDIR` | node-local path | ~200 GB | Job lifetime | Fast temporary scratch |
| HPSS (tape) | — | via `hsi`/`htar` | varies | None | Long-term archival |

---

## `$SCRATCH` Auto-Purge Policy

> **Files in `$SCRATCH` that have not been accessed for 8 weeks (56 days) are automatically and permanently deleted without warning.**

Check for files at risk:
```bash
# Find files not accessed in ≥50 days (approaching purge threshold)
lfs find $SCRATCH --atime +50 -maxdepth 3 -type f

# Reset access time (delay purge) by touching files
touch my_important_file.h5

# Better: copy important results to $CFS before they age out
cp -r $SCRATCH/results/ $CFS/my_project/archive/
```

---

## Checking Quotas

```bash
# All your quotas (home, scratch, CFS)
myquota

# Detailed scratch usage
du -sh $SCRATCH/*
lfs quota -u $USER /pscratch

# Home quota
lfs quota -u $USER /global/homes
```

---

## Lustre Striping ($SCRATCH and $CFS)

Striping spreads file data across multiple OSTs (object storage targets), improving parallel I/O bandwidth.

```bash
# Check current stripe settings
lfs getstripe <file_or_dir>

# Set stripe before writing (applies to new files in directory)
lfs setstripe -c 4 my_output_dir/      # stripe across 4 OSTs (small files, many processes)
lfs setstripe -c 64 big_output_dir/    # stripe across 64 OSTs (very large files)
lfs setstripe -c -1 max_stripe_dir/    # use all available OSTs

# Rule of thumb:
# File < 1 GB:   -c 1 to 8
# File 1–10 GB:  -c 8 to 32
# File > 10 GB:  -c 32 to 64 (or -c -1)
```

---

## Using `$TMPDIR` (Node-Local Storage)

Each compute node has a fast local SSD accessible via `$TMPDIR`. Useful for:
- Many small random-access reads
- Staging input data to avoid Lustre contention
- Temporary intermediate files

```bash
# In your job script:
cp $SCRATCH/input.h5 $TMPDIR/input.h5   # stage in
./my_app --input $TMPDIR/input.h5 --output $TMPDIR/output.h5
cp $TMPDIR/output.h5 $SCRATCH/results/  # stage out
```

`$TMPDIR` is cleaned automatically when the job ends.

---

## HPSS Tape Archive

NERSC's High Performance Storage System (HPSS) is for long-term archival.

```bash
# Interactive HPSS shell
hsi

# Inside hsi:
# ls                             # list HPSS directory
# put localfile remotefile       # upload
# get remotefile localfile       # download
# mkdir mydir                    # create directory

# Direct commands
hsi put myfile.tar.gz            # upload
hsi get /home/user/myfile.tar.gz  # download
hsi ls /home/user/               # list

# htar: archive a directory directly to HPSS
htar -cf /home/user/run001.tar -C /path/to/run001 .   # create archive
htar -xf /home/user/run001.tar                         # extract
htar -tf /home/user/run001.tar                         # list contents
```

---

## CFS (Community File System)

`$CFS` is the persistent, long-term project storage at NERSC. No auto-purge.

```bash
# Typical CFS layout for a project
$CFS/my_project/
├── software/      # compiled code, containers
├── data/          # input data sets
├── results/       # completed simulation outputs
└── archive/       # older results

# Access
ls $CFS
echo $CFS       # /global/cfs/cdirs/<proj>
```

CFS is slower than `$SCRATCH` — use `$SCRATCH` for job I/O and copy finished results to `$CFS`.

---

## Best Practices

1. **Always write job output to `$SCRATCH`**, never `$HOME`.
2. **Copy important results to `$CFS` promptly** — don't rely on `$SCRATCH` for anything you need longer than a few weeks.
3. **Use `lfs setstripe`** on output directories before large parallel writes.
4. **Use `$TMPDIR`** for datasets that are read many times per job — copy once, then read from fast local storage.
5. **Archive to HPSS** for any data you want to keep long-term but don't actively use.
6. **Run `myquota` regularly** to avoid unexpected quota-exceeded errors in jobs.
