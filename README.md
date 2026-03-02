# Code for A guide to Inexact Contiguity Constraints

This repository contains code for the paper "A guide to inexact contiguity constraints" 

## Installation

### 1. Install uv

If you don't already have `uv` installed: 

```bash
pip install uv
```

### 2. Clone the Repository

```bash
git clone https://github.com/Ishaanjolly/A-guide-to-inexact-contiguity-constraints
```

### 3. Sync Dependencies

```bash
uv sync
```
This will create a virtual environment, resolve all dependencies from the lockfile, and install them. No need to manually create or activate a virtual environment — `uv run` handles this automatically.

# Solver Requirements

This project uses [Gurobi](https://www.gurobi.com/) as the default MILP solver. Gurobi offers free academic licences for university-affiliated researchers.

If you'd prefer to use an open-source solver, partial support for [SCIP](https://www.scipopt.org/) via PySCIPOpt is available:

```bash
uv run python src/experiment.py --solver scip
```

Note that solve times and solution quality may differ from those reported in the paper when using alternative solvers.


## Citation 

If you use this code in your research, please cite: