"""
Experiment runner functions for redistricting MIP experiments.

Provides helpers to run single enumeration/optimization solves and
sweep over deviations × contiguity × objective grids, saving results
incrementally to CSV after each run.
"""

import pandas as pd

from src.mip import multi_district_mip
from src.utils import (
    get_roots,
    set_euclidean_weights,
    set_hop_M_weights,
    set_euclidean_M_weights,
)


_ASSIGNMENT_FIELDS = {"district", "districts"}


def _without_district_assignments(metrics):
    """Return experiment metrics without node-level district assignments."""
    return {
        key: value for key, value in metrics.items() if key not in _ASSIGNMENT_FIELDS
    }


def run_enumeration_experiment(
    G_base,
    deviations,
    contiguity_models,
    root,
    k=4,
    distance_metric="hop",
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
    distance_metric : str
        'hop' uses unweighted (unit) edges; 'euclidean' sets Euclidean edge weights.
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
    print(f"Distance metric: {distance_metric}")

    G = G_base.copy()
    if distance_metric == "euclidean":
        print("Setting Euclidean edge weights...")
        set_euclidean_weights(G)

    # Distance-dependent contiguity types use weighted distances
    distance_dependent = {"tree", "dist", "dag"}

    seen_distance_independent = set()
    experiments = []
    for deviation in deviations:
        for contiguity in contiguity_models:
            # Skip duplicate runs for distance-independent models (e.g. cut)
            if contiguity not in distance_dependent:
                key = (deviation, contiguity)
                if key in seen_distance_independent:
                    continue
                seen_distance_independent.add(key)

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

        metrics, _ = multi_district_mip(
            G=G,
            deviation_persons=deviation,
            contiguity=contiguity,
            roots=root,
            k=k,
            pool_search=2,
            pool_size=pool_size,
            time_limit=time_limit,
            use_weighted_distances=use_weighted,
        )

        metrics.update(
            {
                "deviation": deviation,
                "contiguity": contiguity,
                "distance_metric": metric_label,
                "roots": root,
            }
        )
        results.append(_without_district_assignments(metrics))

        pd.DataFrame(results).to_csv(results_file, index=False)
        print(f"  Saved to {results_file}")

    return pd.DataFrame(results)


def run_optimization_experiment(
    G_base,
    deviations,
    contiguity_models,
    objectives,
    k,
    distance_metric="euclidean",
    time_limit=1800,
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
    results_file : str
        CSV file to save/append results after every run.

    Returns
    -------
    pandas.DataFrame
        All results collected during the sweep.
    """
    G = G_base.copy()

    roots = get_roots(G, k)
    print(f"Selected roots: {roots}")
    print(f"Distance metric: {distance_metric}")

    if distance_metric == "euclidean":
        print("Setting Euclidean edge weights...")
        set_euclidean_weights(G)
    elif distance_metric == "hop_M":
        print("Setting hierarchical hop-M edge weights...")
        set_hop_M_weights(G)
    elif distance_metric == "euclidean_M":
        print("Setting hierarchical Euclidean-M edge weights...")
        set_euclidean_M_weights(G)

    distance_dependent = {"tree", "dist", "dag"}

    seen_distance_independent = set()
    experiments = []
    for deviation in deviations:
        for contiguity in contiguity_models:
            for objective_type in objectives:
                if contiguity not in distance_dependent:
                    key = (deviation, contiguity, objective_type)
                    if key in seen_distance_independent:
                        continue
                    seen_distance_independent.add(key)

                use_weighted = (
                    distance_metric in {"euclidean", "hop_M", "euclidean_M"}
                    and contiguity in distance_dependent
                )
                contiguity_dist_label = (
                    distance_metric if contiguity in distance_dependent else "N/A"
                )
                experiments.append(
                    {
                        "deviation": deviation,
                        "contiguity": contiguity,
                        "objective_type": objective_type,
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
            f"objective_type={exp['objective_type']}"
        )

        metrics, _ = multi_district_mip(
            G=G,
            deviation_persons=exp["deviation"],
            contiguity=exp["contiguity"],
            objective=exp["objective_type"],
            roots=roots,
            k=k,
            time_limit=time_limit,
            use_weighted_distances=exp["use_weighted"],
        )

        metrics.update(
            {
                "deviation": exp["deviation"],
                "contiguity": exp["contiguity"],
                "objective_type": exp["objective_type"],
                "contiguity_distance": exp["contiguity_distance"],
                "k": k,
                "distance_metric": distance_metric,
            }
        )

        results.append(_without_district_assignments(metrics))

        pd.DataFrame(results).to_csv(results_file, index=False)
        print(f" Saved to {results_file}")

    return pd.DataFrame(results)
