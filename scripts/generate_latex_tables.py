"""
Generate LaTeX optimization and enumeration tables from CSV results.

Usage:
    python scripts/generate_latex_tables.py --optimization
    python scripts/generate_latex_tables.py --optimization --levels blockgroup
    python scripts/generate_latex_tables.py --enumeration
    python scripts/generate_latex_tables.py --enumeration --levels county

Produces optimization tables per graph level and one table per enumeration CSV.
County tables only include hop and euclidean schemes (no _M variants).
Other levels include all four schemes: hop, euclidean, hop_M, euclidean_M.
"""

import argparse
import json
import re
from pathlib import Path

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent.parent
RESULTS_DIR = ROOT_DIR / "results"
DATA_DIR = ROOT_DIR / "data"
LEVELS = ("block", "blockgroup", "county", "tract", "vtd")

# Map CSV contiguity values to display names
CONTIGUITY_DISPLAY = {
    "no_contiguity": "No contiguity",
    "tree": "Tree-based",
    "dist": "Distance",
    "dag": "DAG",
    "cut": "Cut (exact)",
}

# Ordered distance-dependent contiguity models for table rows
CONTIGUITY_ORDER = ["tree", "dist", "dag"]

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
    # For objectives: use comma separator, keep decimals if float.
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

    cut_filename = f"IA_{level}_cut_optimization.csv"
    cut_filepath = RESULTS_DIR / cut_filename
    if cut_filepath.exists():
        results["cut"] = pd.read_csv(cut_filepath)
    else:
        print(f"  Warning: {cut_filename} not found, skipping.")

    no_contiguity_filename = f"IA_{level}_no_contiguity_optimization.csv"
    no_contiguity_filepath = RESULTS_DIR / no_contiguity_filename
    if no_contiguity_filepath.exists():
        results["no_contiguity"] = pd.read_csv(no_contiguity_filepath)
    else:
        print(f"  Warning: {no_contiguity_filename} not found, skipping.")

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
    """Return |V| from the corresponding graph JSON, if available."""
    graph_file = DATA_DIR / f"IA_{level}.json"
    if not graph_file.exists():
        return None
    with graph_file.open(encoding="utf-8") as source:
        graph_data = json.load(source)
    nodes = graph_data.get("nodes")
    return len(nodes) if nodes is not None else None


def _enumeration_context(filepath, df):
    """Return a display name, label slug, and vertex count for enumeration data."""
    stem = filepath.stem.removesuffix("_enumeration")
    if stem.startswith("IA_"):
        level = stem.removeprefix("IA_")
        return f"Iowa at {level} level", f"iowa_{level}", get_node_count(level)

    if "grid" in df.columns and not df["grid"].dropna().empty:
        grid = str(df["grid"].dropna().iloc[0])
        match = re.fullmatch(r"(\d+)x(\d+)", grid)
        node_count = int(match.group(1)) * int(match.group(2)) if match else None
        return f"the {grid} grid", f"grid_{grid}", node_count

    slug = re.sub(r"[^a-zA-Z0-9]+", "_", stem).strip("_").lower()
    return stem.replace("_", " "), slug, None


def generate_enumeration_table(filepath):
    """Generate a LaTeX table from one enumeration-results CSV."""
    df = pd.read_csv(filepath)
    required = {"deviation", "contiguity", "num_solutions", "time_best", "status"}
    missing = required - set(df.columns)
    if missing:
        print(f"  Warning: {filepath.name} missing columns {sorted(missing)}, skipping.")
        return None

    display_name, label_slug, node_count = _enumeration_context(filepath, df)
    node_str = f", where $|V|={node_count}$" if node_count is not None else ""
    sort_columns = [
        column
        for column in ["deviation", "distance_metric", "contiguity"]
        if column in df.columns
    ]
    if sort_columns:
        df = df.sort_values(sort_columns, na_position="first")

    lines = [
        r"\begin{table}[ht]",
        f"\\caption{{Enumeration results for {display_name}{node_str}}}",
        f"\\label{{enumeration_{label_slug}}}",
        r"\centering",
        r"\small",
        r"\begin{tabular}{r|l|l|rrl}",
        r"Deviation & Scheme & Model & Solutions & Time (s) & Status \\\hline",
    ]

    for _, row in df.iterrows():
        contiguity = row.get("contiguity")
        contiguity = "no_contiguity" if pd.isna(contiguity) else str(contiguity)
        model = CONTIGUITY_DISPLAY.get(contiguity, contiguity.replace("_", " "))

        distance_metric = row.get("distance_metric")
        if distance_metric is None or pd.isna(distance_metric):
            scheme = "N/A"
        else:
            scheme = SCHEME_DISPLAY.get(str(distance_metric), str(distance_metric))

        status = str(row.get("status", "")).replace("_", r"\_")
        lines.append(
            f" {format_number(row['deviation'])} & {scheme} & {model} & "
            f"{format_number(row['num_solutions'])} & "
            f"{format_number(row['time_best'], is_time=True)} & {status}" + r" \\"
        )

    lines.extend([r"\end{tabular}", r"\end{table}"])
    return "\n".join(lines)


def generate_single_table(level, schemes, results, objective_type, obj_display_name, node_str):
    """Generate a single LaTeX table for one objective type."""

    lines = []
    lines.append(r"\begin{table}[ht]")
    lines.append(f"\\caption{{{obj_display_name} for Iowa at {level} level{node_str}}}")
    lines.append(f"\\label{{iowa_{objective_type}_{level}}}")
    lines.append(r"\centering")
    lines.append(r"\small")
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

    no_contiguity_df = results.get("no_contiguity")
    if objective_type == "moi":
        no_contiguity_objective = "euclidean_moi"
        if no_contiguity_df is not None:
            available = set(no_contiguity_df["objective_type"].unique())
            for candidate in ["euclidean_moi", "hop_moi", "weighted_moi"]:
                if candidate in available:
                    no_contiguity_objective = candidate
                    break
    else:
        no_contiguity_objective = "cut_edges"

    lines[-1] += " \\hline"
    lb, ub, time_val, nodes = get_row_data(
        no_contiguity_df, "no_contiguity", no_contiguity_objective
    )
    lines.append(
        " N/A & No contiguity & "
        f"{format_number(lb)} & {format_number(ub)} & "
        f"{format_number(time_val, is_time=True)} & {format_number(nodes)}" + r" \\"
    )

    cut_df = results.get("cut")
    if objective_type == "moi":
        cut_objective = "euclidean_moi"
        if cut_df is not None:
            available = set(cut_df["objective_type"].unique())
            for candidate in ["euclidean_moi", "hop_moi", "weighted_moi"]:
                if candidate in available:
                    cut_objective = candidate
                    break
    else:
        cut_objective = "cut_edges"

    lines[-1] += " \\hline"
    lb, ub, time_val, nodes = get_row_data(cut_df, "cut", cut_objective)
    lines.append(
        " N/A & Cut (exact) & "
        f"{format_number(lb)} & {format_number(ub)} & "
        f"{format_number(time_val, is_time=True)} & {format_number(nodes)}" + r" \\"
    )

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


def parse_args():
    """Parse the requested table type."""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--optimization",
        action="store_true",
        help="generate only optimization tables",
    )
    mode.add_argument(
        "--enumeration",
        action="store_true",
        help="generate only enumeration tables",
    )
    parser.add_argument(
        "--levels",
        nargs="+",
        choices=LEVELS,
        help="graph levels to generate, e.g. --levels block county tract",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    run_optimization = args.optimization or not args.enumeration
    run_enumeration = args.enumeration or not args.optimization
    selected_levels = args.levels or list(LEVELS)

    if run_optimization:
        for level in selected_levels:
            print(f"\n{'='*60}")
            print(f"  {level.upper()}")
            print(f"{'='*60}")

            table = generate_table(level)
            if table:
                print(table)
                print()

    if run_enumeration:
        enumeration_files = sorted(RESULTS_DIR.glob("*_enumeration.csv"))
        if args.levels:
            selected_names = {
                f"IA_{level}_enumeration.csv" for level in selected_levels
            }
            enumeration_files = [
                filepath
                for filepath in enumeration_files
                if filepath.name in selected_names
            ]
            missing = selected_names - {filepath.name for filepath in enumeration_files}
            for filename in sorted(missing):
                print(f"  Warning: {filename} not found, skipping.")
        for filepath in enumeration_files:
            print(f"\n{'='*60}")
            print(f"  ENUMERATION: {filepath.name}")
            print(f"{'='*60}")
            table = generate_enumeration_table(filepath)
            if table:
                print(table)
                print()


if __name__ == "__main__":
    main()
