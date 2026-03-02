"""
Experiment runner functions for redistricting MIP experiments.

Provides helpers to run single enumeration/optimization solves and
sweep over deviations × contiguity × objective grids, saving results
incrementally to CSV after each run.
"""

import time
import pandas as pd

from src.mip import single_district_mip, multi_district_mip
from src.utils import get_roots, set_euclidean_weights


def run_single_enumeration(
    G, deviation, contiguity, root, k, pool_size, time_limit, use_weighted=False
):
    """
    Run a single enumeration solve and return a results dict.

    Parameters
    ----------
    G : networkx.Graph
    deviation : int
        Population deviation in persons.
    contiguity : str
        One of 'tree', 'dist', 'dag', 'cut', 'lcut'.
    root : int or list
        Root node ID(s).
    k : int
        Number of districts.
    pool_size : int
        Maximum solutions to enumerate (Gurobi PoolSolutions).
    time_limit : float
        Time limit in seconds.
    use_weighted : bool
        Whether to pass use_weighted_distances=True to the MIP.

    Returns
    -------
    dict
        Keys: num_plans, solve_time, num_callbacks, num_lazy_cuts, status,
        and optionally error_message.
    """
    start_time = time.time()

    try:
        metrics, model = single_district_mip(
            G=G,
            k=k,
            deviation_persons=deviation,
            root=root,
            contiguity=contiguity,
            objective=None,
            verbose=False,
            pool_search=2,
            pool_size=pool_size,
            time_limit=time_limit,
            use_weighted_distances=use_weighted,
        )

        num_unique = model.SolCount
        solve_time = time.time() - start_time

        print(
            f"  Found {num_unique} plans | time: {solve_time:.1f}s | "
            f"callbacks: {metrics['num_callbacks']} | "
            f"lazy cuts: {metrics['num_lazy_cuts']}"
        )

        return {
            "num_plans": num_unique,
            "solve_time": solve_time,
            "num_callbacks": metrics["num_callbacks"],
            "num_lazy_cuts": metrics["num_lazy_cuts"],
            "status": metrics["status"],
        }

    except Exception as e:
        solve_time = time.time() - start_time
        print(f"  ERROR: {e}")

        return {
            "num_plans": 0,
            "solve_time": solve_time,
            "num_callbacks": 0,
            "num_lazy_cuts": 0,
            "status": "ERROR",
            "error_message": str(e),
        }


def run_enumeration_experiment(
    G_base,
    deviations,
    contiguity_models,
    root,
    k=2,
    distance_metric=None,
    pool_size=100_000,
    time_limit=1800,
    results_file="enumeration_results.csv",
):
    """
    Sweep enumeration over deviations × contiguity models, saving results to CSV.

    Parameters
    ----------
    G_base : networkx.Graph
        Base graph (will be copied; not mutated).
    deviations : list of int
        Population deviations in persons, e.g. [100, 200, ..., 1000].
    contiguity_models : list of str
        e.g. ['tree', 'dist', 'dag', 'cut'].
    root : int or list
        Root node ID(s).
    k : int
        Number of districts.
    distance_metric : str or None
        'euclidean' sets Euclidean edge weights; None uses unweighted graph.
    pool_size : int
        Maximum solutions to enumerate per run.
    time_limit : float
        Time limit per solve in seconds.
    results_file : str
        CSV file to save/append results after every run.

    Returns
    -------
    pandas.DataFrame
        All results collected during the sweep.
    """
    print(f"Root(s): {root}")
    print(f"Distance metric: {distance_metric or 'None (unweighted)'}")

    G = G_base.copy()
    if distance_metric == "euclidean":
        print("Setting Euclidean edge weights...")
        set_euclidean_weights(G)

    # Distance-dependent contiguity types use weighted distances
    distance_dependent = {"tree", "dist", "dag"}

    experiments = []
    for deviation in deviations:
        for contiguity in contiguity_models:
            metric_label = (
                distance_metric if contiguity in distance_dependent else "N/A"
            )
            use_weighted = (
                distance_metric == "euclidean" and contiguity in distance_dependent
            )
            experiments.append((deviation, contiguity, metric_label, use_weighted))

    total = len(experiments)
    print(f"\nTotal experiments: {total}")
    print(f"Results will be saved to: {results_file}")
    print("=" * 72)

    results = []
    for idx, (deviation, contiguity, metric_label, use_weighted) in enumerate(
        experiments
    ):
        print(
            f"\n[{idx + 1}/{total}] deviation={deviation} | "
            f"contiguity={contiguity} | distance={metric_label}"
        )

        result = run_single_enumeration(
            G=G,
            deviation=deviation,
            contiguity=contiguity,
            root=root,
            k=k,
            pool_size=pool_size,
            time_limit=time_limit,
            use_weighted=use_weighted,
        )

        result.update(
            {
                "deviation": deviation,
                "contiguity": contiguity,
                "distance_metric": metric_label,
                "roots": root,
            }
        )
        results.append(result)

        pd.DataFrame(results).to_csv(results_file, index=False)
        print(f"  Saved to {results_file}")

    return pd.DataFrame(results)


# ---------------------------------------------------------------------------
# Optimization helpers
# ---------------------------------------------------------------------------


def run_single_optimization(
    G,
    deviation,
    contiguity,
    objective,
    roots,
    k,
    time_limit,
    use_weighted_distances=False,
):
    """
    Run a single optimization solve and return a results dict.

    Parameters
    ----------
    G : networkx.Graph
    deviation : int
        Population deviation in persons.
    contiguity : str
        One of 'tree', 'dist', 'dag', 'cut', 'lcut'.
    objective : str
        Objective name, e.g. 'hop_moi', 'cut_edges', 'inverse_polsby_popper'.
    roots : list of int
        Root node IDs (one per district).
    k : int
        Number of districts.
    time_limit : float
        Time limit in seconds.
    use_weighted_distances : bool
        Whether to pass use_weighted_distances=True to the MIP.

    Returns
    -------
    dict
        Keys: objective_value, solve_time, num_solutions, num_callbacks,
        num_lazy_cuts, status, gap, and optionally error_message.
    """
    start_time = time.time()

    try:
        metrics, model = multi_district_mip(
            G=G,
            k=k,
            deviation_persons=deviation,
            roots=roots,
            contiguity=contiguity,
            objective=objective,
            verbose=False,
            time_limit=time_limit,
            use_weighted_distances=use_weighted_distances,
        )

        solve_time = time.time() - start_time
        obj_val = model.ObjVal if model.SolCount > 0 else None
        gap = model.MIPGap if model.SolCount > 0 else None

        print(
            f"  Status: {metrics['status']} | obj: {obj_val} | "
            f"time: {solve_time:.1f}s"
        )

        return {
            "objective_value": obj_val,
            "solve_time": solve_time,
            "num_solutions": model.SolCount,
            "num_callbacks": metrics["num_callbacks"],
            "num_lazy_cuts": metrics["num_lazy_cuts"],
            "status": metrics["status"],
            "gap": gap,
        }

    except Exception as e:
        solve_time = time.time() - start_time
        print(f"  ERROR: {e}")

        return {
            "objective_value": None,
            "solve_time": solve_time,
            "num_solutions": 0,
            "num_callbacks": 0,
            "num_lazy_cuts": 0,
            "status": "ERROR",
            "gap": None,
            "error_message": str(e),
        }


def run_optimization_experiment(
    G_base,
    deviations,
    contiguity_models,
    objectives,
    k,
    distance_metric="euclidean",
    time_limit=1800,
    root_strategy="corner",
    results_file="optimization_results.csv",
):
    """
    Sweep optimization over deviations × contiguity × objectives, saving to CSV.

    Parameters
    ----------
    G_base : networkx.Graph
        Base graph (will be copied; not mutated).
    deviations : list of int
        Population deviations in persons.
    contiguity_models : list of str
        e.g. ['tree', 'dist', 'dag', 'cut'].
    objectives : list of str
        e.g. ['hop_moi', 'weighted_moi', 'euclidean_moi', 'cut_edges'].
    k : int
        Number of districts.
    distance_metric : str
        'euclidean' sets Euclidean edge weights on contiguity constraints.
    time_limit : float
        Time limit per solve in seconds.
    root_strategy : str
        Passed to get_roots(); one of 'corner', 'east_west', 'north_south'.
    results_file : str
        CSV file to save/append results after every run.

    Returns
    -------
    pandas.DataFrame
        All results collected during the sweep.
    """
    G = G_base.copy()

    roots = get_roots(G, k, root_strategy=root_strategy)
    print(f"Selected roots: {roots}")
    print(f"Distance metric: {distance_metric}")

    if distance_metric == "euclidean":
        print("Setting Euclidean edge weights...")
        set_euclidean_weights(G)

    distance_dependent = {"tree", "dist", "dag"}

    experiments = []
    for deviation in deviations:
        for contiguity in contiguity_models:
            for objective in objectives:
                use_weighted = (
                    distance_metric == "euclidean" and contiguity in distance_dependent
                )
                contiguity_dist_label = (
                    distance_metric if contiguity in distance_dependent else "N/A"
                )
                experiments.append(
                    {
                        "deviation": deviation,
                        "contiguity": contiguity,
                        "objective": objective,
                        "use_weighted": use_weighted,
                        "contiguity_distance": contiguity_dist_label,
                    }
                )

    total = len(experiments)
    print(f"\nTotal experiments: {total}")
    print(f"Results will be saved to: {results_file}")
    print("=" * 72)

    results = []
    for idx, exp in enumerate(experiments):
        print(
            f"\n[{idx + 1}/{total}] deviation={exp['deviation']} | "
            f"contiguity={exp['contiguity']} (dist: {exp['contiguity_distance']}) | "
            f"objective={exp['objective']}"
        )

        result = run_single_optimization(
            G=G,
            deviation=exp["deviation"],
            contiguity=exp["contiguity"],
            objective=exp["objective"],
            roots=roots,
            k=k,
            time_limit=time_limit,
            use_weighted_distances=exp["use_weighted"],
        )

        result.update(
            {
                "deviation": exp["deviation"],
                "contiguity": exp["contiguity"],
                "objective": exp["objective"],
                "contiguity_distance": exp["contiguity_distance"],
                "k": k,
                "distance_metric": distance_metric,
            }
        )

        results.append(result)

        pd.DataFrame(results).to_csv(results_file, index=False)
        print(f"  Saved to {results_file}")

    return pd.DataFrame(results)
