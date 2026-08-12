"""Generate LaTeX tables from optimization and enumeration result CSVs.

Examples:
    uv run python scripts/generate_latex_tables.py
    uv run python scripts/generate_latex_tables.py --optimization
    uv run python scripts/generate_latex_tables.py --optimization --levels county vtd
    uv run python scripts/generate_latex_tables.py --enumeration
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
RESULTS_DIR = ROOT / "results"

LEVELS = ("block", "blockgroup", "county", "tract", "vtd")
LEVEL_DISPLAY = {
    "block": "block",
    "blockgroup": "block-group",
    "county": "county",
    "tract": "tract",
    "vtd": "precinct",
}
LEVEL_LABEL = {
    "block": "block",
    "blockgroup": "blockgroup",
    "county": "county",
    "tract": "tract",
    "vtd": "precinct",
}

DISTANCE_ORDER = ("Hop", "Euclidean", "HopM", "EuclideanM")
DISTANCE_DISPLAY = {
    "hop": "Hop",
    "euclidean": "Euclidean",
    "hopm": "HopM",
    "euclideanm": "EuclideanM",
}

CONTIGUITY_ORDER = ("no_contiguity", "tree", "dist", "dag", "cut")
CONTIGUITY_DISPLAY = {
    "no_contiguity": "No contiguity",
    "tree": "Tree-based",
    "dist": "Distance",
    "dag": "DAG",
    "cut": "Cut (exact)",
}
ENUMERATION_MODEL_DISPLAY = {
    **CONTIGUITY_DISPLAY,
    "cut": "Separator (Exact)",
}

OBJECTIVE_ORDER = ("moi", "cut_edges")
OBJECTIVE_DISPLAY = {
    "moi": "Moment of Inertia",
    "cut_edges": "Cut Edges",
}

MISSING = "--"


def latex_escape(value: object) -> str:
    text = str(value)
    return (
        text.replace("\\", r"\textbackslash{}")
        .replace("&", r"\&")
        .replace("%", r"\%")
        .replace("$", r"\$")
        .replace("#", r"\#")
        .replace("_", r"\_")
        .replace("{", r"\{")
        .replace("}", r"\}")
        .replace("~", r"\textasciitilde{}")
        .replace("^", r"\textasciicircum{}")
    )


def normalize_key(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower()).strip("_")


def normalize_compact(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value).strip().lower())


def first_value(row: dict[str, str], aliases: Iterable[str]) -> str | None:
    normalized = {normalize_key(k): v for k, v in row.items()}
    for alias in aliases:
        value = normalized.get(normalize_key(alias))
        if value is not None and str(value).strip() != "":
            return str(value).strip()
    return None


def parse_number(value: object) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if text == "" or text.lower() in {"nan", "none", "null", "inf", "-inf", "--"}:
        return None
    text = text.replace(",", "")
    try:
        number = float(text)
    except ValueError:
        return None
    if not math.isfinite(number):
        return None
    return number


def first_number(row: dict[str, str], aliases: Iterable[str]) -> float | None:
    for alias in aliases:
        value = first_value(row, (alias,))
        number = parse_number(value)
        if number is not None:
            return number
    return None


def format_number(value: float | None, *, decimals: int | None = None) -> str:
    if value is None:
        return MISSING
    if decimals is not None:
        return f"{value:,.{decimals}f}"
    if abs(value - round(value)) < 1e-6:
        return f"{round(value):,}"
    return f"{value:,.2f}"


def format_time(value: float | None) -> str:
    return format_number(value, decimals=2)


def format_enumeration_time(value: float | None) -> str:
    return format_number(value, decimals=3)


def format_obj_interval(lb: float | None, ub: float | None) -> str:
    if lb is None and ub is None:
        return MISSING
    if lb is None:
        return format_number(ub)
    if ub is None:
        return format_number(lb)
    if abs(lb - ub) <= 1e-6 * max(1.0, abs(lb), abs(ub)):
        return format_number(ub)
    return f"[{format_number(lb)},{format_number(ub)}]"


def caption_node_count(value: int | None) -> str:
    if value is None:
        return ""
    formatted = format(value, ",").replace(",", r"\text{,}")
    return rf", where $|V|={formatted}$"


def get_node_count(level: str) -> int | None:
    candidates = (
        DATA_DIR / f"IA_{level}.json",
        DATA_DIR / f"IA_{level}_dual_graph.json",
        DATA_DIR / f"IA_{level}_graph.json",
        DATA_DIR / f"{level}.json",
    )
    for path in candidates:
        if not path.exists():
            continue
        with path.open() as handle:
            graph = json.load(handle)
        if isinstance(graph, dict):
            nodes = graph.get("nodes")
            if isinstance(nodes, list):
                return len(nodes)
            adjacency = graph.get("adjacency")
            if isinstance(adjacency, dict):
                return len(adjacency)
            graph_data = graph.get("graph")
            if isinstance(graph_data, dict) and isinstance(
                graph_data.get("nodes"), list
            ):
                return len(graph_data["nodes"])
    return None


def infer_distance_from_filename(path: Path, level: str) -> str | None:
    prefix = f"IA_{level}_"
    suffix = "_optimization.csv"
    if not (path.name.startswith(prefix) and path.name.endswith(suffix)):
        return None
    middle = path.name[len(prefix) : -len(suffix)]
    if middle in {"cut", "no_contiguity"}:
        return None
    return middle or None


def normalize_distance(value: object | None) -> str | None:
    if value is None:
        return None
    compact = normalize_compact(value)
    if compact in {"", "na", "n/a", "none", "null", "notapplicable"}:
        return None
    return DISTANCE_DISPLAY.get(compact, str(value).strip())


def normalize_contiguity(value: object | None) -> str:
    compact = normalize_compact(value)
    if compact in {"", "none", "null", "nocontiguity", "no"}:
        return "no_contiguity"
    if compact in {"tree", "treebased", "treebase"}:
        return "tree"
    if compact in {"dist", "distance", "distancebased"}:
        return "dist"
    if compact == "dag":
        return "dag"
    if compact in {"cut", "cutexact", "exactcut"}:
        return "cut"
    return compact


def normalize_objective(value: object | None) -> str | None:
    compact = normalize_compact(value)
    if compact in {
        "moi",
        "hopmoi",
        "weightedmoi",
        "euclideanmoi",
        "moment",
        "momentofinertia",
        "inertia",
        "compactness",
        "compactnessobjective",
    }:
        return "moi"
    if compact in {"cut", "cuts", "cutedge", "cutedges", "cutedgesobjective"}:
        return "cut_edges"
    if compact in {"node", "nodes", "numnodes", "nodeobjective", "nodesobjective"}:
        return "nodes"
    return None


def objective_from_row(row: dict[str, str]) -> str | None:
    value = first_value(
        row,
        (
            "objective_name",
            "objective_type",
            "optimization_objective",
            "objective_model",
            "target",
            "objective",
            "obj",
        ),
    )
    return normalize_objective(value)


def optimization_values(
    row: dict[str, str],
) -> tuple[float | None, float | None, float | None, float | None]:
    lb = first_number(
        row,
        (
            "lower_bound",
            "lb",
            "best_bound",
            "dual_bound",
            "objective_bound",
            "obj_bound",
        ),
    )
    ub = first_number(
        row,
        (
            "upper_bound",
            "ub",
            "objective_value",
            "best_objective",
            "incumbent",
            "primal_bound",
            "obj_value",
            "objective",
            "value",
        ),
    )
    time_s = first_number(
        row,
        (
            "time",
            "time_s",
            "runtime",
            "runtime_s",
            "solve_time",
            "solve_time_s",
            "elapsed_time",
            "time_best",
        ),
    )
    nodes = first_number(
        row,
        (
            "nodes",
            "bnb_nodes",
            "branch_and_bound_nodes",
            "branch_bound_nodes",
        ),
    )
    return lb, ub, time_s, nodes


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def load_optimization_rows(level: str) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for path in sorted(RESULTS_DIR.glob(f"IA_{level}_*_optimization.csv")):
        if path.name.endswith("_enumeration.csv"):
            continue
        inferred_distance = infer_distance_from_filename(path, level)
        for raw in read_csv(path):
            objective = objective_from_row(raw)
            if objective is None:
                continue
            distance = normalize_distance(
                first_value(raw, ("distance_metric", "distance", "scheme", "metric"))
                or inferred_distance
            )
            contiguity = normalize_contiguity(
                first_value(raw, ("contiguity", "contiguity_model", "model"))
            )
            rows.append(
                {
                    "distance": distance,
                    "contiguity": contiguity,
                    "objective": objective,
                    "values": optimization_values(raw),
                }
            )
    return rows


def ordered_distances(rows: list[dict[str, object]]) -> list[str]:
    seen = {str(row["distance"]) for row in rows if row.get("distance")}
    ordered = [distance for distance in DISTANCE_ORDER if distance in seen]
    ordered.extend(sorted(seen.difference(ordered)))
    if not ordered:
        ordered = list(DISTANCE_ORDER)
    return ordered


def available_models(rows: list[dict[str, object]]) -> list[str]:
    seen = {str(row["contiguity"]) for row in rows}
    ordered = [model for model in CONTIGUITY_ORDER if model in seen]
    ordered.extend(sorted(seen.difference(ordered)))
    return ordered


def find_optimization_row(
    rows: list[dict[str, object]],
    *,
    distance: str,
    model: str,
    objective: str,
) -> tuple[float | None, float | None, float | None, float | None] | None:
    for row in rows:
        if (
            row.get("distance") == distance
            and row.get("contiguity") == model
            and row.get("objective") == objective
        ):
            return row["values"]  # type: ignore[return-value]
    if model in {"cut", "no_contiguity"}:
        for row in rows:
            if (
                row.get("distance") is None
                and row.get("contiguity") == model
                and row.get("objective") == objective
            ):
                return row["values"]  # type: ignore[return-value]
    return None


def optimization_cells(
    rows: list[dict[str, object]],
    *,
    distance: str,
    model: str,
    objective: str,
) -> list[str]:
    values = find_optimization_row(
        rows, distance=distance, model=model, objective=objective
    )
    if values is None:
        return [MISSING, MISSING, MISSING]
    lb, ub, time_s, nodes = values
    return [format_obj_interval(lb, ub), format_time(time_s), format_number(nodes)]


def generate_optimization_table(level: str) -> str | None:
    rows = load_optimization_rows(level)
    if not rows:
        return None

    distances = ordered_distances(rows)
    models = available_models(rows)
    scheme_models = [model for model in models if model not in {"no_contiguity", "cut"}]
    independent_models = [
        model
        for model in ("no_contiguity", "cut")
        if any(
            find_optimization_row(
                rows,
                distance="N/A",
                model=model,
                objective=objective,
            )
            is not None
            for objective in OBJECTIVE_ORDER
        )
    ]
    column_spec = "l|l|" + "|".join("rrr" for _ in OBJECTIVE_ORDER)
    span_headers = " & ".join(
        rf"\multicolumn{{3}}{{c{'|' if i < len(OBJECTIVE_ORDER) - 1 else ''}}}{{{OBJECTIVE_DISPLAY[obj]}}}"
        for i, obj in enumerate(OBJECTIVE_ORDER)
    )
    metric_headers = " & ".join("OBJ & Time (s) & Nodes" for _ in OBJECTIVE_ORDER)
    display = LEVEL_DISPLAY.get(level, level)
    label = LEVEL_LABEL.get(level, level)
    node_count = get_node_count(level)

    lines = [
        r"\begin{table}[H]",
        rf"\caption{{Compactness objectives for Iowa at {display}-level{caption_node_count(node_count)}}}",
        rf"\label{{iowa_optimization_{label}}}",
        r"\centering",
        rf"\begin{{tabular}}{{{column_spec}}}",
        rf"& & {span_headers}\\",
        rf"Scheme & Model & {metric_headers}\\\hline",
    ]

    distance_groups: list[tuple[str, list[str]]] = []
    for distance in distances:
        included_models = [
            model
            for model in scheme_models
            if any(
                find_optimization_row(
                    rows,
                    distance=distance,
                    model=model,
                    objective=objective,
                )
                is not None
                for objective in OBJECTIVE_ORDER
            )
        ]
        if included_models:
            distance_groups.append((distance, included_models))

    for distance_index, (distance, included_models) in enumerate(distance_groups):
        for model_index, model in enumerate(included_models):
            scheme = latex_escape(distance) if model_index == 0 else ""
            model_label = CONTIGUITY_DISPLAY.get(model, model)
            cells: list[str] = []
            for objective in OBJECTIVE_ORDER:
                cells.extend(
                    optimization_cells(
                        rows,
                        distance=distance,
                        model=model,
                        objective=objective,
                    )
                )
            line_end = r" \\"
            if (
                distance_index < len(distance_groups) - 1 or independent_models
            ) and model_index == len(included_models) - 1:
                line_end = r" \\ \hline"
            lines.append(
                f"{scheme} & {latex_escape(model_label)} & {' & '.join(cells)}{line_end}"
            )

    for model_index, model in enumerate(independent_models):
        model_label = CONTIGUITY_DISPLAY.get(model, model)
        cells = []
        for objective in OBJECTIVE_ORDER:
            cells.extend(
                optimization_cells(
                    rows,
                    distance="N/A",
                    model=model,
                    objective=objective,
                )
            )
        line_end = r" \\"
        if model_index < len(independent_models) - 1:
            line_end = r" \\ \hline"
        lines.append(
            f"N/A & {latex_escape(model_label)} & {' & '.join(cells)}{line_end}"
        )

    lines.extend([r"\end{tabular}", r"\end{table}"])
    return "\n".join(lines)


def enumeration_key(row: dict[str, str]) -> tuple[str | None, str, float]:
    distance = normalize_distance(
        first_value(row, ("distance_metric", "distance", "scheme", "metric"))
    )
    contiguity = normalize_contiguity(
        first_value(row, ("contiguity", "contiguity_model", "model"))
    )
    deviation = first_number(row, ("deviation",)) or 0
    return distance, contiguity, deviation


def valid_enumeration_rows(path: Path) -> list[dict[str, str]]:
    rows = read_csv(path)
    required = {"deviation", "contiguity", "num_solutions", "time_best", "status"}
    if not rows or not required.issubset({normalize_key(k) for k in rows[0]}):
        return []
    return rows


def grid_size_from_rows(rows: list[dict[str, str]], path: Path) -> str | None:
    for row in rows:
        grid = first_value(row, ("grid",))
        if grid:
            return grid.replace("x", r"$\times$")
    match = re.search(r"(?P<rows>\d+)x(?P<cols>\d+)", path.stem)
    if match:
        return rf"{match.group('rows')}$\times${match.group('cols')}"
    return None


def first_enumeration_result(
    rows: list[dict[str, str]],
    *,
    contiguity: str,
    deviation: float = 0,
) -> tuple[float | None, float | None, str | None]:
    for row in rows:
        _, row_contiguity, row_deviation = enumeration_key(row)
        if row_contiguity == contiguity and row_deviation == deviation:
            return (
                first_number(row, ("num_solutions", "solutions")),
                first_number(row, ("time_best", "time", "runtime")),
                first_value(row, ("status",)),
            )
    return None, None, None


def generate_grid_enumeration_table(paths: list[Path]) -> str | None:
    square: dict[str, list[dict[str, str]]] = {}
    triangular: dict[str, list[dict[str, str]]] = {}
    for path in paths:
        rows = valid_enumeration_rows(path)
        if not rows:
            continue
        size = grid_size_from_rows(rows, path)
        if not size:
            continue
        target = triangular if "_tri" in path.stem else square
        target[size] = rows

    sizes = sorted(
        set(square) | set(triangular),
        key=lambda size: int(re.match(r"(\d+)", size).group(1))
        if re.match(r"(\d+)", size)
        else 0,
    )
    if not sizes:
        return None

    models = ["tree", "dist", "dag", "cut"]
    lines = [
        r"\begin{table}[ht]",
        r"\caption{Enumeration results for grid graphs}",
        r"\label{tb:grid_graphs}",
        r"\centering",
        r"\begin{tabular}{l|l|rr|rr}",
        r"& & \multicolumn{2}{c|}{Square Grids} & \multicolumn{2}{c}{Triangular Grids}\\",
        r"Size & Model & \# Soln & Time & \# Soln & Time \\\hline",
    ]

    for size_index, size in enumerate(sizes):
        for model_index, model in enumerate(models):
            square_solutions, square_time, _ = first_enumeration_result(
                square.get(size, []),
                contiguity=model,
            )
            triangular_solutions, triangular_time, _ = first_enumeration_result(
                triangular.get(size, []),
                contiguity=model,
            )
            line_end = r" \\"
            if size_index < len(sizes) - 1 and model_index == len(models) - 1:
                line_end = r" \\ \hline"
            lines.append(
                " & ".join(
                    (
                        size if model_index == 0 else "",
                        latex_escape(ENUMERATION_MODEL_DISPLAY.get(model, model)),
                        format_number(square_solutions),
                        format_enumeration_time(square_time),
                        format_number(triangular_solutions),
                        format_enumeration_time(triangular_time),
                    )
                )
                + line_end
            )

    lines.extend([r"\end{tabular}", r"\end{table}"])
    return "\n".join(lines)


def format_iowa_solution_cell(row: dict[str, str] | None) -> str:
    if row is None:
        return MISSING
    solutions = format_number(first_number(row, ("num_solutions", "solutions")))
    status = first_value(row, ("status",)) or ""
    return f"{solutions}*" if status == "Time Limit" else solutions


def generate_iowa_enumeration_table(paths: list[Path]) -> str | None:
    rows: list[dict[str, str]] = []
    for path in paths:
        rows.extend(valid_enumeration_rows(path))
    if not rows:
        return None

    positive_deviations = sorted(
        {
            int(deviation)
            for row in rows
            if (deviation := first_number(row, ("deviation",))) is not None
            and deviation > 0
        }
    )
    if not positive_deviations:
        positive_deviations = sorted(
            {
                int(deviation)
                for row in rows
                if (deviation := first_number(row, ("deviation",))) is not None
            }
        )
    if not positive_deviations:
        return None

    row_lookup: dict[tuple[str | None, str, int], dict[str, str]] = {}
    for row in rows:
        distance, contiguity, deviation = enumeration_key(row)
        row_lookup[(distance, contiguity, int(deviation))] = row

    schemes_seen = {distance for distance, _, _ in row_lookup if distance}
    schemes = [scheme for scheme in DISTANCE_ORDER if scheme in schemes_seen]
    schemes.extend(sorted(schemes_seen.difference(schemes)))
    models = [
        model
        for model in ("tree", "dist", "dag")
        if any(key[1] == model for key in row_lookup)
    ]
    if not schemes or not models:
        return None

    deviation_headers = " & ".join(
        rf"$\pm {deviation}$" for deviation in positive_deviations
    )
    column_spec = "l|l|" + "r" * len(positive_deviations)
    label = (
        "iowa_enumeration"
        if len(paths) == 1
        else f"iowa_{normalize_key('_'.join(path.stem for path in paths))}"
    )
    lines = [
        r"\begin{table}[ht]",
        r"\caption{Enumeration results for Iowa (* indicates timeout)}",
        rf"\label{{{label}}}",
        r"\centering",
        rf"\begin{{tabular}}{{{column_spec}}}",
        rf" & & \multicolumn{{{len(positive_deviations)}}}{{c}}{{Number of solutions, by deviation}} \\",
        rf"Scheme & Model & {deviation_headers} \\\hline",
    ]

    for scheme_index, scheme in enumerate(schemes):
        for model_index, model in enumerate(models):
            values = [
                format_iowa_solution_cell(row_lookup.get((scheme, model, deviation)))
                for deviation in positive_deviations
            ]
            line_end = r" \\"
            if scheme_index < len(schemes) - 1 and model_index == len(models) - 1:
                line_end = r" \\ \hline"
            lines.append(
                " & ".join(
                    (
                        latex_escape(scheme) if model_index == 0 else "",
                        latex_escape(ENUMERATION_MODEL_DISPLAY.get(model, model)),
                        *values,
                    )
                )
                + line_end
            )

    lines.extend([r"\end{tabular}", r"\end{table}"])
    return "\n".join(lines)


def optimization_tables(levels: Iterable[str]) -> list[str]:
    return [table for level in levels if (table := generate_optimization_table(level))]


def enumeration_tables(levels: Iterable[str]) -> list[str]:
    selected = set(levels)
    tables: list[str] = []
    iowa_paths = [
        path
        for path in sorted(RESULTS_DIR.glob("IA_*_enumeration.csv"))
        if (match := re.match(r"IA_(?P<level>.+)_enumeration\.csv", path.name))
        and match.group("level") in selected
    ]
    iowa_table = generate_iowa_enumeration_table(iowa_paths)
    if iowa_table:
        tables.append(iowa_table)
    return tables


def all_enumeration_tables() -> list[str]:
    tables: list[str] = []
    grid_paths = [
        path
        for path in sorted(RESULTS_DIR.glob("*_enumeration.csv"))
        if not path.name.startswith("IA_")
    ]
    grid_table = generate_grid_enumeration_table(grid_paths)
    if grid_table:
        tables.append(grid_table)
    tables.extend(enumeration_tables(LEVELS))
    return tables


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate LaTeX tables from result CSVs.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--optimization",
        action="store_true",
        help="Generate optimization tables.",
    )
    parser.add_argument(
        "--enumeration",
        action="store_true",
        help="Generate enumeration tables.",
    )
    parser.add_argument(
        "--levels",
        nargs="+",
        choices=LEVELS,
        help="One or more Iowa geographic levels to include.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    generate_optimization = args.optimization or not args.enumeration
    generate_enumeration = args.enumeration or not args.optimization
    selected_levels = args.levels or list(LEVELS)

    tables: list[str] = []
    if generate_optimization:
        tables.extend(optimization_tables(selected_levels))
    if generate_enumeration:
        if args.levels:
            tables.extend(enumeration_tables(selected_levels))
        else:
            tables.extend(all_enumeration_tables())

    print("\n\n".join(tables))


if __name__ == "__main__":
    main()
