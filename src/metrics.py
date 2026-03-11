import math


def polsby_popper(G, district, label):
    """
    Compute the Polsby-Popper compactness score for a single district.

    Parameters
    ----------
    G : networkx.Graph
        Graph with node attributes ``area``, ``boundary_perim``, ``boundary_node``
        and edge attribute ``shared_perim``.
    district : iterable
        Node IDs belonging to the district.
    label : dict
        Mapping of node ID to district index.

    Returns
    -------
    float
        Score in (0, 1]; higher is more compact.
    """
    area = sum(G.nodes[i]["area"] for i in district)
    perim = sum(
        G.edges[u, v]["shared_perim"]
        for u in district
        for v in G.neighbors(u)
        if label[u] != label[v]
    )
    perim += sum(
        G.nodes[i]["boundary_perim"] for i in district if G.nodes[i]["boundary_node"]
    )
    return 4 * math.pi * area / (perim * perim)


def create_label_mapping(districts):
    """
    Build a node-to-district index mapping.

    Parameters
    ----------
    districts : list of iterables
        Each element is a collection of node IDs for one district.

    Returns
    -------
    dict
        Maps each node ID to its district index.
    """
    return {i: j for j in range(len(districts)) for i in districts[j]}


def average_polsby_popper(G, districts, verbose=False):
    """
    Compute the mean Polsby-Popper score across all districts.

    Parameters
    ----------
    G : networkx.Graph
        See ``polsby_popper``.
    districts : list of iterables
        District node sets.
    verbose : bool, optional
        Print per-district scores. Default False.

    Returns
    -------
    float
        Mean Polsby-Popper score.
    """
    label = create_label_mapping(districts)
    if verbose:
        print("\nDistrict Polsby-Popper scores:")
        for p, d in enumerate(districts):
            print(p, round(polsby_popper(G, d, label), 4))
    scores = [polsby_popper(G, district, label) for district in districts]
    return sum(scores) / len(scores)


def bottleneck_polsby_popper(G, districts, verbose=False):
    """
    Compute the worst (minimum) Polsby-Popper score across all districts.

    Parameters
    ----------
    G : networkx.Graph
        See ``polsby_popper``.
    districts : list of iterables
        District node sets.
    verbose : bool, optional
        Print per-district scores. Default False.

    Returns
    -------
    float
        Minimum Polsby-Popper score.
    """
    label = create_label_mapping(districts)
    if verbose:
        print("\nDistrict Polsby-Popper scores:")
        for p in range(len(districts)):
            print(p, round(polsby_popper(G, districts[p], label), 4))
    scores = [polsby_popper(G, district, label) for district in districts]
    return min(scores)


def cut_edges(G, districts):
    """
    Count edges that cross district boundaries.

    Parameters
    ----------
    G : networkx.Graph
        Graph of geographic units.
    districts : list of iterables
        District node sets.

    Returns
    -------
    int
        Number of cut edges.
    """
    label = create_label_mapping(districts)
    return sum(1 for i, j in G.edges if label[i] != label[j])


def total_deviation(G, districts, verbose=False):
    """
    Compute population deviation between the largest and smallest district.

    Parameters
    ----------
    G : networkx.Graph
        Graph with node attribute ``TOTPOP``.
    districts : list of iterables
        District node sets.
    verbose : bool, optional
        Print per-district populations. Default False.

    Returns
    -------
    int
        Difference between maximum and minimum district population.
    """
    populations = [
        sum(G.nodes[i]["TOTPOP"] for i in district) for district in districts
    ]
    if verbose:
        print("\nDistrict populations:")
        for p in range(len(districts)):
            print(p, populations[p])
    return max(populations) - min(populations)
