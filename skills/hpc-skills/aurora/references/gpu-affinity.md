# Aurora CPU and GPU Affinity

> Sources: docs.alcf.anl.gov: Aurora "Running Jobs on Aurora" (binding, CCS, HBM sections) and "Machine Overview"; `mpiexec` behavior verified on Aurora, 2026-10.

How to map MPI ranks and OpenMP threads onto Aurora's 2 CPU sockets, 6 GPUs, and 12 GPU tiles. Behavior below was checked with `mpiexec` (Cray PALS 1.8) on Aurora in October 2026.

---

## Node Topology

| Socket | Usable cores (hyperthreads) | Reserved | GPUs (tiles) |
|--------|-----------------------------|----------|--------------|
| 0 | 1–51 (105–155) | core 0 (threads 0, 104) | 0, 1, 2 (0.0–2.1) |
| 1 | 53–103 (157–207) | core 52 (threads 52, 156) | 3, 4, 5 (3.0–5.1) |

- Hardware threads `i` and `i+104` share a physical core.
- Since March 2025, cores 0 and 52 are reserved for system services. A batch shell's affinity is `1-51,53-103,105-155,157-207`. Binding a rank to thread 0 or 52 fails at launch.
- Each PVC GPU has 2 tiles (stacks). Each tile has 64 Xe cores and 64 GB HBM2e.
- `numactl -H` shows 4 NUMA nodes: 0 and 1 are the DDR on each socket (512 GB each), and 2 and 3 are the HBM on each socket (64 GB each, flat mode).

---

## Device Hierarchy: COMPOSITE vs FLAT

| `ZE_FLAT_DEVICE_HIERARCHY` | Devices visible | Default for |
|----------------------------|-----------------|-------------|
| `COMPOSITE` | 6 GPUs, each with 2 sub-devices (tiles) | Aurora PE (default environment) |
| `FLAT` | 12 devices, one per tile | `frameworks` module (PyTorch, TensorFlow, ...) |

- **Explicit scaling**: one rank per tile, 12 per node. This is the most common choice.
- **Implicit scaling**: one rank per GPU, 6 per node, with the driver spreading work across both tiles.

`ZE_AFFINITY_MASK` values use `gpu.tile` notation in COMPOSITE mode (`0.0`, `0.1`, ..., `5.1`) and plain indices `0`–`11` in FLAT mode.

The default environment also sets `ZE_ENABLE_PCI_ID_DEVICE_ORDER=1` and `ONEAPI_DEVICE_SELECTOR=level_zero:gpu`.

---

## Binding Ranks to GPUs

Without any GPU binding, every rank sees all GPUs and the runtime defaults to device 0, so all ranks on a node share one GPU. Use one of the following methods.

### 1. Wrapper scripts (recommended)

`gpu_tile_compact.sh` and `gpu_dev_compact.sh` are on the default `PATH`. They set `ZE_AFFINITY_MASK` from `PALS_LOCAL_RANKID` and then `exec` your program.

```bash
# 12 ranks/node, one per tile (requires COMPOSITE, the default)
mpiexec -n $((NNODES*12)) --ppn 12 \
    --cpu-bind=list:1-8:9-16:17-24:25-32:33-40:41-48:53-60:61-68:69-76:77-84:85-92:93-100 \
    gpu_tile_compact.sh ./app
# local rank 0 -> 0.0, 1 -> 0.1, 2 -> 1.0, ..., 11 -> 5.1

# 6 ranks/node, one per GPU
mpiexec -n $((NNODES*6)) --ppn 6 \
    --cpu-bind=list:1-16:17-32:33-48:53-68:69-84:85-100 \
    gpu_dev_compact.sh ./app
```

Do not use `gpu_tile_compact.sh` with the `frameworks` module (FLAT mode). For a custom mapping, such as 2 tiles per rank or 24 ranks per node, copy the script (`which gpu_tile_compact.sh`) and edit it. A minimal version:

```bash
#!/bin/bash
num_gpu=6
num_tile=2
gpu_id=$(( (PALS_LOCAL_RANKID / num_tile) % num_gpu ))
tile_id=$(( PALS_LOCAL_RANKID % num_tile ))
export ZE_AFFINITY_MASK=${gpu_id}.${tile_id}
exec "$@"
```

### 2. `mpiexec --gpu-bind`

```bash
# one rank per tile
mpiexec -n 12 --ppn 12 --cpu-bind=list:1-8:9-16:17-24:25-32:33-40:41-48:53-60:61-68:69-76:77-84:85-92:93-100 \
    --gpu-bind=list:0.0:0.1:1.0:1.1:2.0:2.1:3.0:3.1:4.0:4.1:5.0:5.1 ./app

# one rank per GPU (sets ZE_AFFINITY_MASK=0..5)
mpiexec -n 6 --ppn 6 --cpu-bind=list:1-16:17-32:33-48:53-68:69-84:85-100 \
    --gpu-bind=list:0:1:2:3:4:5 ./app
```

- Valid `--gpu-bind` keywords are `none`, `per_task:<gpus_per_rank>`, `single:<ranks_per_gpu>`, and `list:<colon-separated>`. Add a `verbose,` prefix to print the mapping.
- `closest` and `map_gpu:` are **not valid**. The launch fails with `Invalid GPU visibility keyword` (exit 127).
- The ALCF docs report `--gpu-bind=list` failures for whole-GPU lists and in FLAT mode. In October 2026, `list:0:1:2:3:4:5` worked in the default COMPOSITE mode, but if it fails, fall back to the wrapper scripts.

### 3. Manual `ZE_AFFINITY_MASK`

Set `ZE_AFFINITY_MASK` yourself for single-process runs or several concurrent `mpiexec` launches (see below). `ZE_AFFINITY_MASK=0,1` exposes only GPUs 0 and 1. Setting it to all six GPUs does nothing useful.

---

## Binding Ranks and Threads to CPUs

| Form | Behavior |
|------|----------|
| `--cpu-bind=list:1-8:9-16:...` | Each `:`-separated set goes to one local rank. **Recommended**, since it keeps every rank on the socket of its GPU. |
| `--depth=D --cpu-bind=depth` | Consecutive blocks of `D` hardware threads, skipping reserved cores. A block can straddle the sockets: with `--depth=8` and 12 ranks, rank 6 gets `49-51,53-57`. |
| `--cpu-bind=depth` (no `--depth`) | One hardware thread per rank. |
| `--cpu-bind=depth:17` | **Not valid syntax, silently ignored.** You get one hardware thread per rank. Use `--depth=17`. |
| `--cpu-bind=core`, `numa`, `socket`, `none` | Coarser built-in policies |

`--depth=17 --cpu-bind=depth` with 6 ranks happens to align with the sockets (`1-17, 18-34, 35-51, 53-69, 70-86, 87-103`), because each socket has 51 usable cores.

### Hybrid MPI + OpenMP

```bash
# 12 ranks/node x 8 threads, one rank per tile
export OMP_NUM_THREADS=8
export OMP_PLACES=cores
export OMP_PROC_BIND=close
mpiexec -n $((NNODES*12)) --ppn 12 \
    --cpu-bind=list:1-8:9-16:17-24:25-32:33-40:41-48:53-60:61-68:69-76:77-84:85-92:93-100 \
    gpu_tile_compact.sh ./app

# 6 ranks/node x 16 threads, one rank per GPU
export OMP_NUM_THREADS=16
mpiexec -n $((NNODES*6)) --ppn 6 \
    --cpu-bind=list:1-16:17-32:33-48:53-68:69-84:85-100 \
    gpu_dev_compact.sh ./app
```

To use both hyperthreads, put them in the list (for example `1-8,105-112`) and set `OMP_PLACES=threads`.

ALCF's helper script [`get_cpu_bind_aurora`](https://github.com/argonne-lcf/pbs_utils/blob/main/get_cpu_bind_aurora) generates `--cpu-bind` lists for other layouts.

---

## Multiple Compute Command Streamers (CCS)

Each tile has 4 compute command streamers. Exposing 2 or 4 of them splits the tile's execution units into independent pools, so that up to 48 ranks per node can share the GPUs. This is similar to NVIDIA MPS.

```bash
# COMPOSITE mode: 4 CCS on both tiles of all 6 GPUs
export ZEX_NUMBER_OF_CCS=0:4,1:4,2:4,3:4,4:4,5:4
# FLAT mode: list all 12 tile-devices
export ZEX_NUMBER_OF_CCS=0:4,1:4,2:4,3:4,4:4,5:4,6:4,7:4,8:4,9:4,10:4,11:4
```

`ZE_AFFINITY_MASK` is applied first, so `ZEX_NUMBER_OF_CCS` refers to the masked device IDs.

---

## Several Applications on One Node

```bash
export OMP_NUM_THREADS=1
export ZE_AFFINITY_MASK=0.0; mpiexec -n 4 --ppn 4 --cpu-bind=list:1:2:3:4     ./app_a &
export ZE_AFFINITY_MASK=0.1; mpiexec -n 4 --ppn 4 --cpu-bind=list:5:6:7:8     ./app_b &
export ZE_AFFINITY_MASK=3.0; mpiexec -n 4 --ppn 4 --cpu-bind=list:53:54:55:56 ./app_c &
wait
```

Pair GPUs 3–5 with cores on socket 1 (53–103).

---

## Using CPU HBM

The CPUs run in flat mode: `malloc` uses DDR (NUMA 0 and 1), and HBM is NUMA 2 (socket 0) and NUMA 3 (socket 1).

```bash
mpiexec -n 2 --ppn 2 --cpu-bind=list:1-51:53-103 --mem-bind=list:2:3 ./app   # rank 0 -> HBM0, rank 1 -> HBM1
mpiexec -n 1 --cpu-bind=list:1-51 numactl --preferred 2 ./app                # prefer HBM, fall back to DDR
```

You can also allocate HBM explicitly with the `memkind` library (`hbw_malloc`).

---

## Verifying a Mapping

```bash
mpiexec -n 12 --ppn 12 --cpu-bind=verbose,list:... --gpu-bind=verbose,list:... ./app
# or wrap a probe:
mpiexec ... gpu_tile_compact.sh bash -c 'echo $PALS_RANKID $(taskset -cp $$) $ZE_AFFINITY_MASK'
```

The ALCF docs include a full MPI+OpenMP+SYCL affinity test program (`hello_affinity_aurora.cpp`) in "Running Jobs on Aurora".
