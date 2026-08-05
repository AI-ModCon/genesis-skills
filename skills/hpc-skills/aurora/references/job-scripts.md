# Aurora Job Script Examples

Aurora uses PBS. All jobs require `-A <project>` and `-l filesystems=<tokens>`.

---

## Full-Node GPU Job (oneAPI/SYCL)

```bash
#!/bin/bash
#PBS -N sycl_job
#PBS -A myproject
#PBS -q prod
#PBS -l select=4:ncpus=104:ngpus=6
#PBS -l walltime=01:00:00
#PBS -l filesystems=home:flare
#PBS -o sycl_job.out
#PBS -e sycl_job.err

cd $PBS_O_WORKDIR

module use /soft/modulefiles
module load oneapi/eng-compiler/2024.06.28.002

# Select all Intel GPU devices via Level Zero
export ONEAPI_DEVICE_SELECTOR=level_zero:*

# mpiexec is the launcher on Aurora (not srun/mpirun)
# 6 GPUs per node × 4 nodes = 24 total GPU tasks
mpiexec -n 24 -ppn 6 \
    --cpu-bind=depth \
    --gpu-bind=closest \
    ./my_sycl_app
```

---

## Full-Node CPU-Only Job

```bash
#!/bin/bash
#PBS -N cpu_job
#PBS -A myproject
#PBS -q prod
#PBS -l select=8:ncpus=104:mpiprocs=104:mem=512gb
#PBS -l walltime=02:00:00
#PBS -l filesystems=home:flare

cd $PBS_O_WORKDIR

module use /soft/modulefiles
module load oneapi/eng-compiler/2024.06.28.002

mpiexec -n 832 -ppn 104 ./my_mpi_app
```

---

## OpenMP Offload (GPU via OpenMP target)

```bash
#!/bin/bash
#PBS -N omp_offload
#PBS -A myproject
#PBS -q debug
#PBS -l select=1:ncpus=104:ngpus=6
#PBS -l walltime=01:00:00
#PBS -l filesystems=home:flare

cd $PBS_O_WORKDIR

module use /soft/modulefiles
module load oneapi/eng-compiler/2024.06.28.002

export OMP_TARGET_OFFLOAD=MANDATORY

# Compile: icpx -fiopenmp -fopenmp-targets=spir64 -O3 app.cpp -o app
mpiexec -n 6 -ppn 6 ./my_omp_offload_app
```

---

## Hybrid MPI + OpenMP + GPU

```bash
#!/bin/bash
#PBS -N hybrid_gpu
#PBS -A myproject
#PBS -q prod
#PBS -l select=2:ncpus=104:ngpus=6:mpiprocs=6:ompthreads=17
#PBS -l walltime=04:00:00
#PBS -l filesystems=home:flare

cd $PBS_O_WORKDIR

module use /soft/modulefiles
module load oneapi/eng-compiler/2024.06.28.002

export OMP_NUM_THREADS=17
export ONEAPI_DEVICE_SELECTOR=level_zero:*

# 6 MPI ranks per node, each using 1 GPU and 17 OpenMP threads
mpiexec -n 12 -ppn 6 \
    --cpu-bind=depth:17 \
    --gpu-bind=closest \
    ./my_hybrid_app
```

---

## DAOS-Backed Job

```bash
#!/bin/bash
#PBS -N daos_job
#PBS -A myproject
#PBS -q prod
#PBS -l select=2:ncpus=104:ngpus=6
#PBS -l walltime=02:00:00
#PBS -l filesystems=home:flare
#PBS -o daos_job.out

cd $PBS_O_WORKDIR

module use /soft/modulefiles
module load oneapi/eng-compiler/2024.06.28.002
module load daos

# Mount DAOS container as POSIX filesystem
DAOS_POOL="mypool"
DAOS_CONT="mycontainer"
MOUNT_POINT="/tmp/daos_$PBS_JOBID"

mkdir -p "$MOUNT_POINT"
dfuse --pool "$DAOS_POOL" --container "$DAOS_CONT" --mountpoint "$MOUNT_POINT" \
    --foreground &
DFUSE_PID=$!
sleep 5   # wait for mount

# Use it like a regular filesystem
mpiexec -n 12 -ppn 6 ./my_app --data "$MOUNT_POINT/input" --out "$MOUNT_POINT/output"

# Cleanup
fusermount3 -u "$MOUNT_POINT"
kill $DFUSE_PID 2>/dev/null
```

---

## Job Array on Aurora

```bash
#!/bin/bash
#PBS -N sweep
#PBS -A myproject
#PBS -q prod
#PBS -t 1-50%5                       # max 5 running at once
#PBS -l select=1:ncpus=104:ngpus=6
#PBS -l walltime=01:00:00
#PBS -l filesystems=home:flare

cd $PBS_O_WORKDIR

module use /soft/modulefiles
module load oneapi/eng-compiler/2024.06.28.002

INPUT="inputs/case_${PBS_ARRAY_INDEX}.json"
OUTPUT="outputs/result_${PBS_ARRAY_INDEX}.h5"

mpiexec -n 6 -ppn 6 ./my_sim --input "$INPUT" --output "$OUTPUT"
```

---

## Interactive Session

```bash
qsub -I \
  -A myproject \
  -q debug \
  -l select=1:ncpus=104:ngpus=6 \
  -l walltime=1:00:00 \
  -l filesystems=home:flare

# Once inside the interactive session:
cd /lus/flare/projects/myproject/
module use /soft/modulefiles
module load oneapi/eng-compiler/2024.06.28.002

# Test your application
mpiexec -n 6 -ppn 6 ./my_app --test
```

---

## Data Pre/Post Processing (CPU only)

```bash
#!/bin/bash
#PBS -N preprocess
#PBS -A myproject
#PBS -q prod
#PBS -l select=1:ncpus=104:mpiprocs=104
#PBS -l walltime=00:30:00
#PBS -l filesystems=home:flare

cd /lus/flare/projects/myproject/

module load python/3.11

# Run Python preprocessing (uses CPU only)
mpiexec -n 104 python -m mpi4py.futures preprocess.py \
    --input raw_data/ \
    --output preprocessed/
```

---

## Common `mpiexec` Options on Aurora

| Option | Effect |
|--------|--------|
| `-n <N>` | Total MPI ranks |
| `-ppn <N>` | Ranks per node |
| `--cpu-bind=depth` | Bind CPUs depth-first (good for threading) |
| `--cpu-bind=list:<list>` | Explicit CPU binding |
| `--gpu-bind=closest` | Bind GPU to closest CPU socket |
| `--gpu-bind=map_gpu:<map>` | Explicit GPU binding |
| `-env VAR=val` | Set environment variable for all ranks |
| `--hosts <list>` | Restrict to specific nodes |
