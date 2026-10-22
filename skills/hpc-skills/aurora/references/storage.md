# Aurora Storage Reference

---

## Filesystem Overview

| Name | `filesystems=` name | Path | Size / default quota | Use for |
|------|---------------------|------|----------------------|---------|
| Home (Gecko Lustre) | `home` | `/home/<user>` (served from `/lus/gecko/home`) | 50 GB default per user | Source code, configs, small files |
| Flare (Lustre) | `flare` | `/lus/flare/projects/<project>` | 91 PB, 650 GB/s peak; 1 TB default per project | Job I/O; submit jobs from here |
| DAOS | `daos_user` (or `daos_perf` for approved teams) | `/tmp/<pool>/<container>` once mounted with `dfuse` | ~200 PB usable, >24 TB/s peak write; pools on request | High-bandwidth I/O and checkpointing |

- The PBS submit hook maps each name to a resource: `home_fs`, `flare_fs`, `daos_user_fs`, `daos_perf_fs`. Either spelling is accepted. `qstat -Bf | grep -A2 valid_filesystems` lists them.
- **`grand` and `eagle` are Polaris filesystems.** They are not mounted on Aurora, and `qsub` rejects them (`Invalid filesystem identifiers grand, eagle`). Move data from Eagle with Globus (below).
- Nothing on Aurora is backed up. DAOS can still lose data in rare cases, so keep important results on Flare and copies elsewhere.
- Project PIs request more Flare quota or a DAOS pool from support@alcf.anl.gov.

```bash
myquota                                  # home and project quotas
```

---

## Flare (Lustre)

Flare has 160 OSTs and 40 MDTs. Set striping on output directories before writing large shared files in parallel:

```bash
lfs getstripe /lus/flare/projects/<project>/run1
lfs setstripe -c 16 /lus/flare/projects/<project>/run1          # new files in run1 inherit this
```

Small files and file-per-process output should keep the default stripe count (1). Large shared files benefit from higher counts. Use `-c -1` (all 160 OSTs) only for very large files written by many nodes. ALCF's Lustre striping guide: https://www.alcf.anl.gov/support-center/training-assets/file-systems-and-io-performance

Importing Python packages or loading shared libraries from Flare on thousands of nodes at once can overload the metadata servers. Use Copper (see [programming-env.md](programming-env.md)).

---

## DAOS

DAOS (Distributed Asynchronous Object Storage) is a separate object store, not a filesystem path. It is reached through containers inside a per-project **pool**.

- Total: about 230 PB from 1,024 servers. In the current configuration, about 200 PB on 800 servers is available to users.
- Bandwidth depends on how many servers your pool spans and on the container's redundancy factor.
- It is in a pre-production stability period: expect occasional slowdowns or outages, and treat data loss as possible.

### Getting Access

Email support@alcf.anl.gov with the project name, ALCF usernames, the space you need (typically 100 TB or more), a justification, and a preferred pool name. The pool label is usually the project name.

### Setup

```bash
module use /soft/modulefiles
module load daos

DAOS_POOL=<pool>
DAOS_CONT=<container>

daos pool query ${DAOS_POOL}                        # space, targets, rebuild status
daos container create --type=POSIX ${DAOS_POOL} ${DAOS_CONT}
daos cont list ${DAOS_POOL}
daos container get-prop ${DAOS_POOL} ${DAOS_CONT}
daos container destroy ${DAOS_POOL} ${DAOS_CONT}    # permanent
```

The pool and container are **positional arguments**, not `--pool`/`--label` options.

### Redundancy

ALCF recommends redundancy factor 3 for anything you care about. This uses erasure coding 16+3 for files and 4-way replication for directories:

```bash
daos container create --type=POSIX --chunk-size=2097152 \
    --properties=rd_fac:3,ec_cell_sz:131072,cksum:crc32,srv_cksum:on \
    --file-oclass=EC_16P3G32 --dir-oclass=RP_4G1 \
    ${DAOS_POOL} ${DAOS_CONT}
```

`rd_fac:0` (no redundancy) is fastest, but losing a single SSD loses data. The property is `rd_fac`, not `rf`.

### Mounting with dfuse

```bash
# Compute nodes (inside a job with -l filesystems=...:daos_user):
launch-dfuse.sh ${DAOS_POOL}:${DAOS_CONT}     # clush across all nodes; mounts /tmp/<pool>/<container>
ls /tmp/${DAOS_POOL}/${DAOS_CONT}
clean-dfuse.sh ${DAOS_POOL}:${DAOS_CONT}      # optional; the PBS epilogue also unmounts

# Login node:
mkdir -p /tmp/${USER}/${DAOS_POOL}/${DAOS_CONT}
start-dfuse.sh -m /tmp/${USER}/${DAOS_POOL}/${DAOS_CONT} --pool ${DAOS_POOL} --cont ${DAOS_CONT}
fusermount3 -u /tmp/${USER}/${DAOS_POOL}/${DAOS_CONT}    # always unmount on login nodes
```

### Running against DAOS

```bash
mpiexec --no-vni --env LD_PRELOAD=/usr/lib64/libpil4dfs.so -n ... --ppn ... ./app
```

- `--no-vni` is currently required for DAOS jobs.
- `libpil4dfs` intercepts both data and metadata calls, which gives performance close to the native DFS API with no code changes.
- Other access paths: MPI-IO (ROMIO hints such as `romio_cb_write enable`, `cb_config_list *:8`, `striping_unit 2097152`), HDF5, the DFS C API (examples in `/soft/daos/examples/src/`), and PyDAOS for PyTorch data loading (`module load daos_perf` with `filesystems=...:daos_perf`).
- A container in `UNCLEAN` status (seen in `daos cont get-prop`) blocks mounts. Contact support.

---

## Data Transfer

### Globus (recommended)

- **Flare:** the Globus collection `alcf#dtn_flare`.
- **Eagle (Polaris) ↔ Flare:** transfer between `alcf#dtn_eagle` and `alcf#dtn_flare`.
- **Home:** only Globus Connect Personal, run on a login node. See the ALCF docs, "Transferring Files through Globus".

### scp / rsync

```bash
scp data.tar.gz <user>@aurora.alcf.anl.gov:/lus/flare/projects/<project>/
```

Each new connection asks for a MobilePASS+ or hardware-token passcode. An SSH `ControlMaster` lets you reuse one authenticated connection.

### Moving data into DAOS

- Small data: copy into a mounted container with ordinary Unix tools, or use `daos filesystem copy --src <flare path> --dst daos://<pool>/<cont>/<path>` without mounting.
- Large data: `module load mpifileutils daos`, then run `dcp` (distributed copy) under `mpiexec`.

See the ALCF docs, "Moving data across filesystems".

---

## Best Practices

1. List every filesystem the job touches in `-l filesystems=`. If one of them is marked down, the job stays queued instead of failing at runtime.
2. Run jobs out of `/lus/flare/projects/<project>`, not `$HOME`.
3. Set Lustre striping on directories that will hold large shared files.
4. Use DAOS for bandwidth-bound I/O with `rd_fac:3` containers, and copy results you need to keep to Flare.
5. Use Copper for Python or shared-library loading at large node counts.
