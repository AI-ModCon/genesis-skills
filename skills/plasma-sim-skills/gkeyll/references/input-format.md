# Gkeyll Lua Input File Format

All gkeyll simulations are driven by Lua scripts. Each script has four sections.

## Section 1: App Require

Load the physics App for your simulation type:

```lua
local Plasma = require("App.Plasma").VlasovMaxwell   -- fully kinetic
-- or
local Plasma = require("App.Plasma").Gyrokinetic     -- gyrokinetic
-- or
local Plasma = require("App.Plasma").Moments         -- fluid moments
-- or
local Plasma = require("App.Plasma").PKPM            -- 10-moment
```

## Section 2: Preamble

Declare constants, user parameters, and derived quantities:

```lua
-- Physical constants
local eV     = Plasma.Constants.ELEMENTARY_CHARGE
local eps0   = Plasma.Constants.EPSILON_0
local mu0    = Plasma.Constants.MU_0
local me     = Plasma.Constants.ELECTRON_MASS
local mp     = Plasma.Constants.PROTON_MASS

-- User parameters
local Te = 100 * eV    -- electron temperature
local Ti = 100 * eV    -- ion temperature
local n0 = 1e19        -- number density (m^-3)
local B0 = 1.0         -- background magnetic field (T)

-- Derived
local vte  = math.sqrt(Te / me)        -- electron thermal speed
local vti  = math.sqrt(Ti / mp)        -- ion thermal speed
local wpe  = math.sqrt(n0 * eV^2 / (eps0 * me))  -- electron plasma freq
local de   = Plasma.Constants.SPEED_OF_LIGHT / wpe  -- electron skin depth
```

## Section 3: App Configuration Table

### Common Parameters (all Apps)

```lua
local plasmaApp = Plasma.App {
   -- Timing
   tEnd   = 1e-6,      -- end time (seconds in SI, or normalized)
   nFrame = 20,        -- number of output frames

   -- Configuration space
   lower = {-math.pi * de},   -- lower bounds (one per dimension)
   upper = { math.pi * de},   -- upper bounds
   cells = {128},              -- number of cells per dimension

   -- Numerics
   timeStepper = "rk3",        -- "rk2", "rk3" (default), "rk4"
   cflFrac     = 0.9,          -- CFL safety factor (< 1)

   -- Parallelism
   periodicDirs = {1},         -- periodic directions (1=x, 2=y, 3=z)
   decompCuts   = {4},         -- MPI decomposition per dimension
   useShared    = true,        -- shared memory within nodes
```

### Species Block

Each species is a named entry in the App table:

```lua
   elc = Plasma.Species {
      -- Velocity-space domain
      lower = {-6 * vte, -6 * vte},   -- vx, vy lower bounds
      upper = { 6 * vte,  6 * vte},   -- vx, vy upper bounds
      cells = {32, 32},               -- velocity space resolution

      -- Species properties
      charge = -eV,
      mass   = me,

      -- Initial condition (function of x, vx, vy, ...)
      init = Plasma.MaxwellianProjection {
         density     = function(t, xn) return n0 end,
         driftSpeed  = function(t, xn) return 0.0 end,
         temperature = function(t, xn) return Te end,
      },

      -- Collisions (optional)
      coll = Plasma.LBOCollisions { collFreq = 1e7 },

      -- Sources (optional)
      source = Plasma.Source { ... },

      -- Boundary conditions (optional, for non-periodic)
      bcx = { Plasma.Species.bcReflect, Plasma.Species.bcReflect },

      -- Diagnostics
      diagnostics = { "M0", "M1i", "M2", "intM0", "intM2" },
   },
```

Common diagnostic strings:

| String | Quantity |
|--------|---------|
| `"M0"` | Number density |
| `"M1i"` | Momentum density |
| `"M2"` | Energy density |
| `"intM0"` | Integrated particle count |
| `"intM2"` | Integrated energy |
| `"pkpm"` | PKPM pressures |

### Field Block (VlasovMaxwell / Moments)

```lua
   field = Plasma.Field {
      epsilon0 = eps0,
      mu0      = mu0,

      -- Initial fields (functions of position)
      init = function(t, xn)
         local x = xn[1]
         local Ex, Ey, Ez = 0.0, 0.0, 0.0
         local Bx, By, Bz = 0.0, 0.0, B0
         return Ex, Ey, Ez, Bx, By, Bz
      end,

      -- Boundary conditions (non-periodic dirs only)
      bcx = { Plasma.Field.bcReflect, Plasma.Field.bcReflect },

      evolveField = true,     -- set false to hold fields fixed
   },
```

### ExternalField Block (optional)

```lua
   externalField = Plasma.ExternalField {
      -- Static background field
      init = function(t, xn)
         return 0.0, 0.0, 0.0, 0.0, 0.0, B0
      end,
   },
```

### Gyrokinetic App Specifics

```lua
local Plasma = require("App.Plasma").Gyrokinetic

local plasmaApp = Plasma.App {
   -- Geometry
   coordinateMap = Plasma.RectangularProjectionCoordMap { ... },

   -- Normalization
   chargeE = eV,

   elc = Plasma.Species {
      charge = -eV, mass = me,
      lower = {-6*vte}, upper = {6*vte},   -- v_par only
      cells = {32},
      muNumCells = 8,                        -- mu grid cells
      init = ...,
   },
   ...
}
```

## Section 4: Run

```lua
plasmaApp:run()
```

## Annotated Example: 1D Weibel Instability

```lua
local Plasma = require("App.Plasma").VlasovMaxwell

local eV   = Plasma.Constants.ELEMENTARY_CHARGE
local me   = Plasma.Constants.ELECTRON_MASS
local eps0 = Plasma.Constants.EPSILON_0
local mu0  = Plasma.Constants.MU_0
local c    = Plasma.Constants.SPEED_OF_LIGHT

local vt   = 0.2 * c      -- thermal velocity (non-relativistic)
local kx   = 2 * math.pi  -- wavenumber

local plasmaApp = Plasma.App {
   tEnd   = 40.0 / (vt * kx),
   nFrame = 20,
   lower  = {0.0},
   upper  = {2 * math.pi / kx},
   cells  = {64},
   periodicDirs = {1},

   elcUp = Plasma.Species {
      charge = -eV, mass = me,
      lower  = {-6*vt, -6*vt},
      upper  = { 6*vt,  6*vt},
      cells  = {32, 32},
      init   = Plasma.MaxwellianProjection {
         density     = function(t, xn) return 0.5 end,
         driftSpeed  = function(t, xn) return  vt end,
         temperature = function(t, xn) return me * vt^2 / eV end,
      },
      diagnostics = {"M0", "M1i", "M2"},
   },
   elcDn = Plasma.Species {
      charge = -eV, mass = me,
      lower  = {-6*vt, -6*vt},
      upper  = { 6*vt,  6*vt},
      cells  = {32, 32},
      init   = Plasma.MaxwellianProjection {
         density     = function(t, xn) return 0.5 end,
         driftSpeed  = function(t, xn) return -vt end,
         temperature = function(t, xn) return me * vt^2 / eV end,
      },
      diagnostics = {"M0", "M1i", "M2"},
   },

   field = Plasma.Field {
      epsilon0 = eps0,
      mu0      = mu0,
      init = function(t, xn) return 0,0,0, 0,0,0 end,
   },
}
plasmaApp:run()
```
