# PBS Job Script Examples

Annotated, ready-to-use templates for common HPC workload patterns.

---

## Single-Node CPU Job

```bash
#!/bin/bash
#PBS -N cpu_job                      # job name
#PBS -A myproject                    # account/project (usually required)
#PBS -l select=1:ncpus=32:mem=64gb   # 1 node, 32 cores, 64 GB
#PBS -l walltime=04:00:00
#PBS -q workq                        # queue name
#PBS -o cpu_job.out
#PBS -e cpu_job.err
#PBS -j n                            # keep stdout/stderr separate

cd $PBS_O_WORKDIR

module purge
module load gcc/12 openmpi/4.1

# Single MPI task using all 32 CPUs
mpiexec -n 32 ./my_application --input input.dat --output output.dat
```

---

## Multi-Node MPI Job

```bash
#!/bin/bash
#PBS -N mpi_job
#PBS -A myproject
#PBS -l select=8:ncpus=128:mem=256gb:mpiprocs=128
#PBS -l walltime=02:00:00
#PBS -q workq
#PBS -o mpi_job.out
#PBS -e mpi_job.err
#PBS -V                              # export current environment to job

cd $PBS_O_WORKDIR

module purge
module load gcc/12 openmpi/4.1

echo "Running $PBS_NP tasks on $PBS_NUM_NODES nodes"
echo "Node list: $(cat $PBS_NODEFILE | sort -u | tr '\n' ' ')"

mpiexec -n $PBS_NP -hostfile $PBS_NODEFILE ./my_mpi_app
```

Note: `mpiprocs=128` in the select statement sets MPI ranks per chunk; `$PBS_NP` = total ranks = 8 × 128.

---

## GPU Job

```bash
#!/bin/bash
#PBS -N gpu_job
#PBS -A myproject
#PBS -l select=2:ncpus=32:ngpus=4:mem=128gb
#PBS -l walltime=06:00:00
#PBS -q gpu
#PBS -o gpu_job.out
#PBS -e gpu_job.err

cd $PBS_O_WORKDIR

module purge
module load cuda/12.1 gcc/12 openmpi/4.1

# Total GPUs: 2 nodes × 4 GPUs = 8 GPUs
mpiexec -n 8 -npernode 4 ./my_cuda_app
```

---

## OpenMP Single-Node (Threaded) Job

```bash
#!/bin/bash
#PBS -N omp_job
#PBS -A myproject
#PBS -l select=1:ncpus=64:ompthreads=64:mem=128gb
#PBS -l walltime=02:00:00
#PBS -q workq

cd $PBS_O_WORKDIR
module load gcc/12

export OMP_NUM_THREADS=64
export OMP_PLACES=cores
export OMP_PROC_BIND=close

./my_openmp_app
```

---

## Hybrid MPI + OpenMP

```bash
#!/bin/bash
#PBS -N hybrid_job
#PBS -A myproject
#PBS -l select=4:ncpus=64:mpiprocs=4:ompthreads=16:mem=128gb
#PBS -l walltime=03:00:00
#PBS -q workq
#PBS -o hybrid.out

cd $PBS_O_WORKDIR
module load gcc/12 openmpi/4.1

# 4 nodes × 4 MPI ranks/node = 16 total ranks, each with 16 OpenMP threads
export OMP_NUM_THREADS=16
export OMP_PLACES=cores
export OMP_PROC_BIND=close

mpiexec -n 16 -npernode 4 ./my_hybrid_app
```

Check: `mpiprocs × ompthreads` should equal `ncpus` per chunk (4 × 16 = 64 ✓).

---

## Job Array

```bash
#!/bin/bash
#PBS -N sweep
#PBS -A myproject
#PBS -t 1-100                        # task indices 1..100
# #PBS -t 1-100%10                   # max 10 running at once
#PBS -l select=1:ncpus=8:mem=16gb
#PBS -l walltime=00:30:00
#PBS -q workq
#PBS -o logs/sweep_${PBS_JOBID}_${PBS_ARRAY_INDEX}.out
#PBS -e logs/sweep_${PBS_JOBID}_${PBS_ARRAY_INDEX}.err

mkdir -p logs outputs

cd $PBS_O_WORKDIR

INPUT_FILE="inputs/input_${PBS_ARRAY_INDEX}.dat"
OUTPUT_FILE="outputs/output_${PBS_ARRAY_INDEX}.dat"

./my_application --input "$INPUT_FILE" --output "$OUTPUT_FILE"
```

---

## Interactive Job

```bash
# Request 1 node, 16 CPUs, 1 hour interactively
qsub -I -l select=1:ncpus=16:mem=32gb -l walltime=01:00:00 -q debug -A myproject

# Once the shell opens on the compute node:
module load gcc openmpi
./my_app
exit    # returns to login node and releases allocation
```

---

## Job with Email Notification

```bash
#!/bin/bash
#PBS -N important_job
#PBS -A myproject
#PBS -l select=16:ncpus=128:mem=512gb
#PBS -l walltime=12:00:00
#PBS -q workq
#PBS -m abe                          # email on Abort, Begin, End
#PBS -M myuser@institution.edu
#PBS -o important.out
#PBS -e important.err

cd $PBS_O_WORKDIR
module load gcc/12 openmpi/4.1
mpiexec -n 2048 ./my_large_app
```

---

## Using `$PBS_NODEFILE`

For MPI launchers that require an explicit hostfile:

```bash
# Print the node list
sort -u $PBS_NODEFILE

# Count unique nodes
sort -u $PBS_NODEFILE | wc -l

# mpirun with explicit hostfile
mpirun -hostfile $PBS_NODEFILE -np $PBS_NP ./my_app

# mpiexec (OpenMPI) with per-node rank count
mpiexec --machinefile $PBS_NODEFILE -n $PBS_NP ./my_app
```

Note: `$PBS_NODEFILE` lists each slot (CPU) on each node, so the same hostname appears multiple times. Use `sort -u` for unique node list.

---

## Staging Data In/Out

```bash
#!/bin/bash
#PBS -N staged_job
#PBS -A myproject
#PBS -l select=1:ncpus=32:mem=64gb
#PBS -l walltime=02:00:00
#PBS -q workq

WORK_DIR="/scratch/$USER/${PBS_JOBID}"
INPUT="/project/myproject/data/large_input.h5"
OUTPUT="/project/myproject/results/"

# Stage in
mkdir -p "$WORK_DIR"
cp "$INPUT" "$WORK_DIR/input.h5"

cd "$WORK_DIR"
module load gcc/12
./my_application --input input.h5 --output result.h5

# Stage out
cp result.h5 "$OUTPUT/${PBS_JOBID}_result.h5"

# Clean up scratch
rm -rf "$WORK_DIR"
```
