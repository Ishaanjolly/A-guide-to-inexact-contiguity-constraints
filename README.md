# Code for A guide to Inexact Contiguity Constraints

Code implication for the paper *A Guide to Inexact Contiguity Constraints*. It
contains the optimization, feasibility, and enumeration experiments used to
study practical relaxations of geographic contiguity constraints in political
districting.

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

## Navigating the notebooks

Open the repository root in JupyterLab or VS Code, then select the **Inexact
Contiguity** kernel and run a notebook from top to bottom. The notebooks are
grouped by workflow:

- `notebooks/optimization/` contains Iowa optimization experiments. Use the
  county, block, or `precint` notebook for the corresponding graph level.
- `notebooks/feasibility/` checks enacted maps under the Hop, Euclidean, HopM,
  and EuclideanM constraints.
- `notebooks/enumeration/` contains Iowa and synthetic-grid enumeration
  experiments.

Experiment notebooks write CSV output to `results/`; use the table generator
below after an experiment finishes. Run cells in order because the early cells
define the graph, model, and experiment parameters used later in the notebook.

## Generating LaTeX tables

The table generator reads experiment CSVs from `results/` and prints LaTeX to
standard output.

Generate all optimization tables:

```bash
uv run python scripts/generate_latex_tables.py --optimization
```

Generate optimization tables for selected graph levels:

```bash
uv run python scripts/generate_latex_tables.py --optimization \
  --levels county block vtd
```

Generate all enumeration tables:

```bash
uv run python scripts/generate_latex_tables.py --enumeration
```

Generate enumeration tables for selected Iowa graph levels:

```bash
uv run python scripts/generate_latex_tables.py --enumeration \
  --levels county block vtd
```

Available Iowa levels are `county`, `block`, and `vtd` (precinct). The
`--levels` option accepts one or more values. Without `--levels`, optimization
tables are generated for all three levels; enumeration also includes
synthetic-grid results. Without either mode flag, both optimization and
enumeration tables are generated.

Optimization tables load distance-specific results plus the separate
`no_contiguity` and `cut` result files. Enumeration mode discovers files named
`*_enumeration.csv`, including synthetic-grid results. Vertex counts are read
from the corresponding graph JSON in `data/` when available.

### Solver Requirements

This project uses [Gurobi](https://www.gurobi.com/) as the default MILP solver.
Gurobi offers free academic licences for university-affiliated researchers.
