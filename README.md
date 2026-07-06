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
  --levels block blockgroup county
```

Generate all enumeration tables:

```bash
uv run python scripts/generate_latex_tables.py --enumeration
```

Generate enumeration tables for selected Iowa graph levels:

```bash
uv run python scripts/generate_latex_tables.py --enumeration \
  --levels county tract
```

Available levels are `block`, `blockgroup`, `county`, `tract`, and `vtd`.
The `--levels` option accepts one or more values. Without `--levels`, all
available results are processed. Without either mode flag, both optimization
and enumeration tables are generated.

Optimization tables load distance-specific results plus the separate
`no_contiguity` and `cut` result files. Enumeration mode discovers files named
`*_enumeration.csv`, including synthetic-grid results. Vertex counts are read
from the corresponding graph JSON in `data/` when available.

### Solver Requirements

This project uses [Gurobi](https://www.gurobi.com/) as the default MILP solver.
Gurobi offers free academic licences for university-affiliated researchers.

## Citation

If you use this code in your research, please cite:
