# Aurora Job Script Examples

Every job needs `-A <project>`, `-l walltime=`, and `-l filesystems=`. Nodes are allocated whole, so request them with `-l select=N` and use `place=scatter`. The server adds `-k doe -r n -W umask=0022` by default. Submit from `/lus/flare/projects/<project>`.

| Nodes | Walltime | Queue |
|-------|----------|-------|
| 1–2 | ≤ 1 hr | `debug` |
| up to 256 | ≤ 1 hr | `debug-scaling` |
| 1–16 | ≤ 7 days | `capacity` |
| 256–10,624 | ≤ 12/18/24 hr by size | `prod` (routes to `small`/`medium`/`large`) |

There is no production queue for 17–255 nodes beyond 1 hour. Use `capacity` for up to 16 nodes, or `prod` with 256 or more.

---

## Debug: 1 Node, 12 Ranks (One per GPU Tile)

```bash
#!/bin/bash -l
#PBS -N tile_test
#PBS -A <project>
#PBS -q debug
#PBS -l select=1
#PBS -l place=scatter
#PBS -l walltime=00:30:00
#PBS -l filesystems=home:flare
#PBS -j oe

cd ${PBS_O_WORKDIR}

NNODES=$(wc -l < ${PBS_NODEFILE})
NRANKS_PER_NODE=12
CPU_BIND="list:1-8:9-16:17-24:25-32:33-40:41-48:53-60:61-68:69-76:77-84:85-92:93-100"

export OMP_NUM_THREADS=1

mpiexec -n $(( NNODES * NRANKS_PER_NODE )) --ppn ${NRANKS_PER_NODE} \
    --cpu-bind=${CPU_BIND} \
    gpu_tile_compact.sh ./my_sycl_app
```

---

## Production: 512 Nodes, 12 Ranks per Node

```bash
#!/bin/bash -l
#PBS -N prod_run
#PBS -A <project>
#PBS -q prod
#PBS -l select=512
#PBS -l place=scatter
#PBS -l walltime=06:00:00
#PBS -l filesystems=home:flare
#PBS -j oe

cd ${PBS_O_WORKDIR}

NNODES=$(wc -l < ${PBS_NODEFILE})
NRANKS_PER_NODE=12
NTOTRANKS=$(( NNODES * NRANKS_PER_NODE ))
CPU_BIND="list:1-8:9-16:17-24:25-32:33-40:41-48:53-60:61-68:69-76:77-84:85-92:93-100"

echo "nodes=${NNODES} ranks=${NTOTRANKS}"

mpiexec -n ${NTOTRANKS} --ppn ${NRANKS_PER_NODE} --cpu-bind=${CPU_BIND} \
    gpu_tile_compact.sh ./my_app
rc=$?
[ $rc -ne 0 ] && echo "mpiexec failed with ${rc}" && exit $rc
```

512 nodes routes to `small` (256–1,024 nodes, 12 hr max). To keep all nodes in one rack (64 nodes, one dragonfly group) or one chassis (8 nodes), add `-l place=scatter:group=tier0` or `group=tier1`. Only request this when the job fits.

---

## Scaling Test: 32 Nodes in `debug-scaling`

```bash
#!/bin/bash -l
#PBS -A <project>
#PBS -q debug-scaling
#PBS -l select=32
#PBS -l place=scatter
#PBS -l walltime=00:45:00
#PBS -l filesystems=home:flare

cd ${PBS_O_WORKDIR}
NNODES=$(wc -l < ${PBS_NODEFILE})
mpiexec -n $(( NNODES * 12 )) --ppn 12 \
    --cpu-bind=list:1-8:9-16:17-24:25-32:33-40:41-48:53-60:61-68:69-76:77-84:85-92:93-100 \
    gpu_tile_compact.sh ./my_app
```

Only one `debug-scaling` job per user can be queued or running at a time.

---

## Hybrid MPI + OpenMP + GPU: 6 Ranks per Node (One per GPU)

```bash
#!/bin/bash -l
#PBS -A <project>
#PBS -q debug
#PBS -l select=2
#PBS -l place=scatter
#PBS -l walltime=01:00:00
#PBS -l filesystems=home:flare

cd ${PBS_O_WORKDIR}

export OMP_NUM_THREADS=16
export OMP_PLACES=cores
export OMP_PROC_BIND=close

NNODES=$(wc -l < ${PBS_NODEFILE})
mpiexec -n $(( NNODES * 6 )) --ppn 6 \
    --cpu-bind=list:1-16:17-32:33-48:53-68:69-84:85-100 \
    gpu_dev_compact.sh ./my_hybrid_app
```

Do not write `--cpu-bind=depth:16`. It is silently ignored and every rank gets one hardware thread. For `depth` binding, write `--depth=16 --cpu-bind=depth`.

---

## OpenMP Target Offload

```bash
# Build (AoT for PVC):
#   mpicxx -fiopenmp -fopenmp-targets=spir64_gen -Xopenmp-target-backend=spir64_gen "-device pvc" app.cpp -o app
export OMP_TARGET_OFFLOAD=MANDATORY
mpiexec -n $(( NNODES * 12 )) --ppn 12 \
    --cpu-bind=list:1-8:9-16:17-24:25-32:33-40:41-48:53-60:61-68:69-76:77-84:85-92:93-100 \
    gpu_tile_compact.sh ./app
```

---

## CPU-Only: 102 Ranks per Node

```bash
#!/bin/bash -l
#PBS -A <project>
#PBS -q capacity
#PBS -l select=8
#PBS -l place=scatter
#PBS -l walltime=12:00:00
#PBS -l filesystems=home:flare

cd ${PBS_O_WORKDIR}
NNODES=$(wc -l < ${PBS_NODEFILE})
export MPIR_CVAR_ENABLE_GPU=0     # skip GPU-aware MPI setup when no GPU buffers are used

# 102 usable physical cores per node (cores 0 and 52 are reserved)
mpiexec -n $(( NNODES * 102 )) --ppn 102 --depth=1 --cpu-bind=depth ./my_mpi_app
```

---

## Long Runs in `capacity` (≤16 Nodes, ≤7 Days)

```bash
#!/bin/bash -l
#PBS -A <project>
#PBS -q capacity
#PBS -l select=4
#PBS -l place=scatter
#PBS -l walltime=72:00:00
#PBS -l filesystems=home:flare

cd ${PBS_O_WORKDIR}
mpiexec -n 48 --ppn 12 \
    --cpu-bind=list:1-8:9-16:17-24:25-32:33-40:41-48:53-60:61-68:69-76:77-84:85-92:93-100 \
    gpu_tile_compact.sh ./my_app
```

`capacity` limits each user to 2 running and 5 queued jobs, and all users together to 512 nodes.

---

## Job Array

```bash
#!/bin/bash -l
#PBS -N sweep
#PBS -A <project>
#PBS -q capacity
#PBS -J 1-4%2
#PBS -r y
#PBS -l select=1
#PBS -l place=scatter
#PBS -l walltime=04:00:00
#PBS -l filesystems=home:flare

cd ${PBS_O_WORKDIR}

INPUT="inputs/case_${PBS_ARRAY_INDEX}.json"
OUTPUT="outputs/result_${PBS_ARRAY_INDEX}.h5"

mpiexec -n 12 --ppn 12 \
    --cpu-bind=list:1-8:9-16:17-24:25-32:33-40:41-48:53-60:61-68:69-76:77-84:85-92:93-100 \
    gpu_tile_compact.sh ./my_sim --input "${INPUT}" --output "${OUTPUT}"
```

- `-J`, not `-t`. `-r y` is required: the default `-r n` makes `qsub` fail with `cannot submit non-rerunable Array Job`.
- Subjobs count against the queue's per-user limits, so arrays larger than 5 will not fit in `capacity`, and `debug` allows only 1 queued job per user.
- For many small tasks, run them inside one larger allocation instead (see "Several Applications on One Node" in [gpu-affinity.md](gpu-affinity.md), or a workflow tool such as Parsl, libEnsemble, or Balsam).

---

## DAOS-Backed Job

```bash
#!/bin/bash -l
#PBS -A <project>
#PBS -q debug-scaling
#PBS -l select=8
#PBS -l place=scatter
#PBS -l walltime=01:00:00
#PBS -l filesystems=flare:daos_user

cd ${PBS_O_WORKDIR}

module use /soft/modulefiles
module load daos

DAOS_POOL=<project_pool>
DAOS_CONT=<container>

# Mount the POSIX container on every node at /tmp/<pool>/<container>
launch-dfuse.sh ${DAOS_POOL}:${DAOS_CONT}

NNODES=$(wc -l < ${PBS_NODEFILE})
mpiexec -n $(( NNODES * 12 )) --ppn 12 --no-vni \
    --env LD_PRELOAD=/usr/lib64/libpil4dfs.so \
    --cpu-bind=list:1-8:9-16:17-24:25-32:33-40:41-48:53-60:61-68:69-76:77-84:85-92:93-100 \
    gpu_tile_compact.sh ./my_app --out /tmp/${DAOS_POOL}/${DAOS_CONT}/run1

# Unmount (the PBS epilogue also does this)
clean-dfuse.sh ${DAOS_POOL}:${DAOS_CONT}
```

- `daos_user` and `daos_user_fs` are both accepted in `filesystems`.
- `--no-vni` is currently required in `mpiexec` for DAOS. The `libpil4dfs` interception library routes POSIX I/O through DAOS without going through the kernel.
- Do not start `dfuse` by hand in a batch script. Run in the background on the head node, it mounts only there, not on the other nodes.

---

## Python / AI Frameworks

Always base Python jobs on `module load frameworks`, not on the Spack `python` module or a personal conda install.

```bash
#!/bin/bash -l
#PBS -A <project>
#PBS -q debug
#PBS -l select=2
#PBS -l place=scatter
#PBS -l walltime=00:30:00
#PBS -l filesystems=home:flare

cd ${PBS_O_WORKDIR}
module load frameworks            # conda env with PyTorch etc.; sets ZE_FLAT_DEVICE_HIERARCHY=FLAT (12 devices/node)

NNODES=$(wc -l < ${PBS_NODEFILE})
mpiexec -n $(( NNODES * 12 )) --ppn 12 \
    --cpu-bind=list:1-8:9-16:17-24:25-32:33-40:41-48:53-60:61-68:69-76:77-84:85-92:93-100 \
    python train.py
```

- In FLAT mode, select the device inside the program (for example with the local rank: `torch.xpu.set_device(local_rank)`). ALCF recommends not using `gpu_tile_compact.sh` with `frameworks`.
- If you import packages from a venv on Flare or home at large node counts (roughly 1,000 nodes or more), use Copper (`module load copper; launch_copper.sh`) to avoid overloading Lustre.

---

## Interactive Session

```bash
cd /lus/flare/projects/<project>
qsub -I -A <project> -q debug -l select=1 -l place=scatter \
     -l walltime=01:00:00 -l filesystems=home:flare

# on the compute node:
cd ${PBS_O_WORKDIR}
mpiexec -n 12 --ppn 12 --cpu-bind=list:1-8:9-16:17-24:25-32:33-40:41-48:53-60:61-68:69-76:77-84:85-92:93-100 \
    gpu_tile_compact.sh ./my_app --test
```

To `ssh` between your allocated nodes, `$HOME` and `$HOME/.ssh` must both have permissions `700`.

---

## Working Around Bad Nodes

```bash
cat ${PBS_NODEFILE} > local.hostfile
# remove known-bad hostnames from local.hostfile, then:
mpiexec --hostfile local.hostfile -n ... --ppn ... ./my_app
```

`-W tolerate_node_failures=all` keeps the job alive when nodes fail. You must then remove the failed nodes yourself (`pbsnodes -l | grep <jobid>`) before the next `mpiexec`. Report bad nodes to support@alcf.anl.gov.

---

## Compute Node Internet Access

Only through the proxy:

```bash
export http_proxy="http://proxy.alcf.anl.gov:3128"
export https_proxy="http://proxy.alcf.anl.gov:3128"
export ftp_proxy="http://proxy.alcf.anl.gov:3128"
```
