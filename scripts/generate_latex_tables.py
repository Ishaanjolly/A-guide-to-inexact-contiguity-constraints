"""
Generate LaTeX optimization tables from CSV results.

Usage:
    python scripts/generate_latex_tables.py

Produces one LaTeX table per graph level (county, tract, blockgroup, vtd, block).
County tables only include hop and euclidean schemes (no _M variants).
Other levels include all four schemes: hop, euclidean, hop_M, euclidean_M.
"""

import pandas as pd
import os
from pathlib import Path

RESULTS_DIR = Path(__file__).resolve().parent.parent / "results"

# Map CSV contiguity values to display names
CONTIGUITY_DISPLAY = {
    "tree": "Tree-based",
    "dist": "Distance",
    "dag": "DAG",
    "cut": "Cut (exact)",
}

# Ordered contiguity models for table rows
CONTIGUITY_ORDER = ["tree", "dist", "dag", "cut"]

# Map distance_metric CSV values to scheme display names
SCHEME_DISPLAY = {
    "hop": "Hop",
    "euclidean": "Euclidean",
    "hop_M": "HopM",
    "euclidean_M": "EuclideanM",
}


def format_number(val, is_time=False):
    """Format a number for the table. Returns '–' for missing/inf."""
    if val is None or pd.isna(val):
        return "–"
    if val == float("inf") or val == float("-inf"):
        return "–"
    if is_time:
        return f"{val:,.2f}"
    # For objectives: use comma separator, keep decimals if float
    if isinstance(val, float) and val != int(val):
        return f"{val:,.2f}"
    else:
        return f"{int(val):,}"


def load_results(level):
    """Load all optimization CSVs for a given level. Returns dict of metric -> DataFrame."""
    results = {}

    if level == "county":
        metrics = ["hop", "euclidean"]
    else:
        metrics = ["hop", "euclidean", "hop_M", "euclidean_M"]

    for metric in metrics:
        filename = f"IA_{level}_{metric}_optimization.csv"
        filepath = RESULTS_DIR / filename
        if filepath.exists():
            results[metric] = pd.read_csv(filepath)
        else:
            print(f"  Warning: {filename} not found, skipping.")

    return results


def get_row_data(df, contiguity, objective_type):
    """Extract LB, UB, Time, Nodes for a given contiguity + objective from a DataFrame."""
    if df is None:
        return None, None, None, None

    mask = (df["contiguity"] == contiguity) & (df["objective_type"] == objective_type)
    rows = df[mask]

    if rows.empty:
        return None, None, None, None

    row = rows.iloc[0]

    # Check if infeasible or no solution
    if row["status"] in ["Infeasible", "Infeasible or Unbounded"]:
        return None, None, None, None
    if row["status"] == "Time Limit" and pd.isna(row.get("objective")):
        return None, None, None, None

    obj = row.get("objective")
    bound = row.get("obj_bound")
    time_val = row.get("time_best")
    nodes = row.get("bnb_nodes")

    # Handle inf bounds
    if bound == float("inf") or bound == float("-inf"):
        bound = None

    return bound, obj, time_val, nodes


def get_node_count(level):
    """Return |V| for the level based on known Iowa graph sizes."""
    counts = {
        "county": 99,
        "tract": 896,
        "blockgroup": 2703,
        "vtd": 1671,
        "block": None,  # will be filled if known
    }
    return counts.get(level)


def generate_single_table(level, schemes, results, objective_type, obj_display_name, node_str):
    """Generate a single LaTeX table for one objective type."""

    lines = []
    lines.append(r"\begin{table}[ht]")
    lines.append(f"\\caption{{{obj_display_name} for Iowa at {level} level{node_str}}}")
    lines.append(f"\\label{{iowa_{objective_type}_{level}}}")
    lines.append(r"\centering")
    lines.append(r"\begin{tabular}{l|l|rrrr} ")
    lines.append(r"Scheme & Model & LB & UB & Time & Nodes \\\hline")

    for scheme_idx, scheme in enumerate(schemes):
        df = results.get(scheme)
        scheme_label = SCHEME_DISPLAY[scheme]

        for row_idx, contiguity in enumerate(CONTIGUITY_ORDER):
            model_label = CONTIGUITY_DISPLAY[contiguity]

            if objective_type == "moi":
                # Determine which MOI objective to use based on scheme
                moi_obj = None
                if df is not None:
                    available = set(df["objective_type"].unique())
                    prefs = {
                        "hop": ["hop_moi", "euclidean_moi"],
                        "euclidean": ["euclidean_moi"],
                        "hop_M": ["weighted_moi", "euclidean_moi"],
                        "euclidean_M": ["euclidean_moi"],
                    }
                    for pref in prefs.get(scheme, ["euclidean_moi"]):
                        if pref in available:
                            moi_obj = pref
                            break
                if moi_obj is None:
                    moi_obj = "euclidean_moi"
                lb, ub, time_val, nodes = get_row_data(df, contiguity, moi_obj)
            else:
                lb, ub, time_val, nodes = get_row_data(df, contiguity, "cut_edges")

            lb_str = format_number(lb)
            ub_str = format_number(ub)
            time_str = format_number(time_val, is_time=True)
            nodes_str = format_number(nodes)

            if row_idx == 0:
                scheme_col = scheme_label
            else:
                scheme_col = ""

            line = f" {scheme_col} & {model_label} & {lb_str} & {ub_str} & {time_str} & {nodes_str} \\\\"
            lines.append(line)

        if scheme_idx < len(schemes) - 1:
            lines[-1] += " \\hline"

    lines.append(r"\end{tabular}")
    lines.append(r"\end{table}")

    return "\n".join(lines)


def generate_table(level):
    """Generate two LaTeX tables (MOI and Cut Edges) for a given level."""
    results = load_results(level)

    if not results:
        print(f"  No results found for {level}")
        return None

    if level == "county":
        schemes = ["hop", "euclidean"]
    else:
        schemes = ["hop", "euclidean", "hop_M", "euclidean_M"]

    node_count = get_node_count(level)
    node_str = f", where $|V|={node_count}$" if node_count else ""

    moi_table = generate_single_table(
        level, schemes, results, "moi", "Moment of Inertia", node_str
    )
    ce_table = generate_single_table(
        level, schemes, results, "cut_edges", "Cut Edges", node_str
    )

    return moi_table + "\n\n" + ce_table


def main():
    levels = ["county", "tract", "blockgroup", "vtd"]

    for level in levels:
        print(f"\n{'='*60}")
        print(f"  {level.upper()}")
        print(f"{'='*60}")

        table = generate_table(level)
        if table:
            print(table)
            print()


if __name__ == "__main__":
    main()
