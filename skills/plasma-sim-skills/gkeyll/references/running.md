# Gkeyll Running Reference

## Basic Commands

```bash
# Serial run
$HOME/gkylsoft/gkeyll/bin/gkeyll input.lua

# MPI parallel run
mpirun -np 4 $HOME/gkylsoft/gkeyll/bin/gkeyll input.lua

# Check if MPI is enabled
$HOME/gkylsoft/gkeyll/bin/gkeyll -help   # look for "Built with MPI"

# C input file (alternative)
$HOME/gkylsoft/gkeyll/bin/cgkeyll input.c

# Convenience alias (add to ~/.bashrc)
alias gkyl="$HOME/gkylsoft/gkeyll/bin/gkeyll"
```

## Output Files

Gkeyll writes output in ADIOS2 BP format:

```
sim_elc_0.bp    # species "elc", frame 0
sim_elc_1.bp    # species "elc", frame 1
sim_field_0.bp  # fields, frame 0
sim_elc_M0_0.bp # diagnostic M0 of "elc", frame 0
```

The prefix `sim` is taken from the input file name (without `.lua`).

## MPI Decomposition

Set `decompCuts` in the App config to control parallelism:

```lua
-- 1D: 4 MPI ranks in x
decompCuts = {4},

-- 2D: 2x2 decomposition
decompCuts = {2, 2},

-- 3D: 4x2x2 = 16 ranks
decompCuts = {4, 2, 2},
```

Total `np` in `mpirun` must equal the product of `decompCuts`.

Shared memory (within a node) can accelerate runs:
```lua
useShared = true,   -- in App table
```

## GPU Runs

For CUDA-enabled builds, gkeyll automatically uses GPUs when available. No extra flags needed in the Lua file. Ensure the binary was built with `--enable-cuda=yes`.

```bash
# Single GPU
$HOME/gkylsoft/gkeyll/bin/gkeyll input.lua

# Multi-GPU with MPI (one rank per GPU)
mpirun -np 4 $HOME/gkylsoft/gkeyll/bin/gkeyll input.lua
```

## HPC Job Script (SLURM example)

```bash
#!/bin/bash
#SBATCH --job-name=gkeyll_run
#SBATCH --nodes=2
#SBATCH --ntasks-per-node=8
#SBATCH --time=04:00:00
#SBATCH --partition=regular

module load openmpi

export PATH=$HOME/gkylsoft/gkeyll/bin:$PATH

mpirun -np 16 gkeyll sim.lua
```

## Post-Processing with Postgkyl

Install postgkyl:
```bash
conda install -c gkyl -c conda-forge postgkyl
# or
pip install postgkyl
```

Basic usage:
```bash
# Plot field at frame 5
pgkyl sim_field_5.bp plot

# Plot electron density vs x, all frames
pgkyl sim_elc_M0_*.bp animate

# Extract and print data
pgkyl sim_elc_M0_0.bp print

# Integrate over velocity space and plot
pgkyl sim_elc_0.bp integrate 1 2 plot   # integrate vx,vy (dims 1,2)
```

Postgkyl Python API:
```python
import postgkyl as pg

data = pg.GData("sim_elc_M0_0.bp")
vals = data.getValues()   # numpy array of field values
grid = data.getGrid()     # list of coordinate arrays
```

## Regression Testing

Run a standard test to verify the installation:
```bash
cd $HOME/gkeyll/Regression/vm-weibel/
mpirun -n 1 $HOME/gkylsoft/gkeyll/bin/gkeyll rt-weibel-2x2v-p2.lua
```

Compare output to reference using postgkyl:
```bash
pgkyl rt-weibel-2x2v-p2_field_0.bp plot
```

## Common Issues

**Segfault at startup**: Usually a LuaJIT version mismatch. Rebuild with the same LuaJIT used during `./configure`.

**`module not found` Lua error**: The input file requires an App module that wasn't built. Check that the required App layer (`vlasov`, `gyrokinetic`, etc.) was compiled.

**MPI rank mismatch**: Ensure `mpirun -np N` where N equals the product of all `decompCuts` values.

**No output files**: Check that the run completed at least one frame (increase `nFrame` or decrease `tEnd`). Look for error messages in stdout/stderr.

**Slow serial performance**: If the binary was built with CUDA, it may still use the GPU even for 1-rank runs. Use a CPU-only build for small/debug runs.
