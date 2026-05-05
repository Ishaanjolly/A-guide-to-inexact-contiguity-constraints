# Code for A guide to Inexact Contiguity Constraints

#### Setup for development with uv

### 1. Install uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Restart your terminal after installing.

#### 2. Clone the repo

```bash
git clone https://github.com/Ishaanjolly/A-guide-to-inexact-contiguity-constraints.git
cd A-guide-to-inexact-contiguity-constraints
```

#### 3. Create and activate the virtual environment

```bash
uv venv inexact_contiguity --python 3.11
source inexact_contiguity/bin/activate
UV_PROJECT_ENVIRONMENT=inexact_contiguity uv sync
```

#### 4. Install dependencies

```bash
uv sync
```

#### 5. Set up the Jupyter kernel

```bash
python -m ipykernel install --user --name=inexact_contiguity --display-name "Inexact Contiguity"
```

#### Solver Requirements

This project uses [Gurobi](https://www.gurobi.com/) as the default MILP solver. Gurobi offers free academic licences for university-affiliated researchers.

If you'd prefer to use an open-source solver, partial support for [SCIP](https://www.scipopt.org/) via PySCIPOpt is available:

```bash
uv run python src/experiment.py
```

Note that solve times and solution quality may differ from those reported in the paper when using alternative solvers.


## Citation 

If you use this code in your research, please cite: