---
name: bmad-ecosystem
description: Use when installing or working with Bmad, Tao, or PyTao for accelerator modeling. Covers lattice syntax, element definitions and physics conventions, Tao initialization and commands, optics calculations, particle tracking, fitting, and Python model access and analysis.
license: GPL-3.0-only
metadata:
  author: Ningdong Wang
---

# Bmad, Tao, and PyTao

## Three layers of Bmad-ecosystem

**Bmad** is the accelerator physics library and lattice language. A Bmad lattice
describes the particle and reference energy, beamline elements, their arrangement,
and the physical models used for calculations.

**Tao** is an interactive user program built on Bmad. It loads lattices, calculates optics,
tracks particles, plots results, and fits adjustable parameters to target data.
Its initialization files establish a session; its commands inspect and change
that session.

**PyTao** exposes a Tao session to Python through the Tao shared library. A
`Tao` object loads a model, runs commands, and returns calculated quantities
for analysis and plotting.

Standalone Tao normally opens a prompt that remains active until `exit`.
Use an interactive session when terminal tools support sending commands to a
running process. For shell automation, [supply a command sequence](references/tao/initialization.md#start-a-session)
ending in `exit`.

| File | What it describes |
| --- | --- |
| `.bmad` | The lattice: elements, lines, reference quantities, and physics settings |
| `tao.init` and related initialization files | Tao namelists: lattices to load, data, variables, beam and plot setup |
| Tao command files, often `.tao` | Commands to execute in a Tao session, including aliases and parameterized scripts |
| Python scripts or notebooks | PyTao calls, numerical analysis, automation, and Python plotting |

## Read for the task

The three guides introduce the concepts and capabilities of each layer. Go
directly to a topic reference when the task is already specific.

| Task | Reference |
| --- | --- |
| Install Bmad/Tao and PyTao or resolve library-loading problems | [Installation](references/installation.md) |
| Understand a lattice or choose a Bmad capability | [Bmad concepts](references/bmad.md) |
| Write definitions, expressions, lines, or includes | [Lattice syntax](references/bmad/lattice-syntax.md) |
| Choose an element and understand its defining attributes | [Elements](references/bmad/elements.md) |
| Interpret coordinates, units, or reference quantities | [Physics conventions](references/bmad/physics-conventions.md) |
| Understand or build a controller | [Controllers](references/bmad/controllers.md) |
| Understand Tao's session and lattice states | [Tao concepts](references/tao.md) |
| Prepare `tao.init`, load lattices, or configure universes | [Initialization](references/tao/initialization.md) |
| Find commands or write a Tao script | [Commands and scripts](references/tao/commands-and-scripts.md) |
| Define data and variables or fit optics | [Data and fitting](references/tao/data-and-fitting.md) |
| Load, query, and analyze a model in Python | [PyTao](references/pytao.md) |
