import math
import networkx as nx


def squared_euclidean_distance(G, i, j):
    """
    Compute squared Euclidean distance between two nodes.

    Parameters
    ----------
    G : networkx.Graph
        Graph with ``X``, ``Y`` attributes on nodes.
    i, j : node
        Node identifiers.

    Returns
    -------
    float
        Squared Euclidean distance.
    """
    dx = G.nodes[i]["X"] - G.nodes[j]["X"]
    dy = G.nodes[i]["Y"] - G.nodes[j]["Y"]
    return dx * dx + dy * dy


def euclidean_distance(G, i, j):
    """
    Compute Euclidean distance between two nodes.

    Parameters
    ----------
    G : networkx.Graph
        Graph with ``X``, ``Y`` attributes on nodes.
    i, j : node
        Node identifiers.

    Returns
    -------
    float
        Euclidean distance.
    """
    return math.sqrt(squared_euclidean_distance(G, i, j))


def set_euclidean_weights(G):
    """
    Set the ``weight`` edge attribute to the Euclidean distance between endpoints.

    Parameters
    ----------
    G : networkx.Graph
        Graph with ``X``, ``Y`` attributes on nodes.
    """
    for i, j in G.edges:
        G.edges[i, j]["weight"] = euclidean_distance(G, i, j)


def _x(G, i):
    return G.nodes[i]["X"]


def _y(G, i):
    return G.nodes[i]["Y"]


def _equals(a, b, epsilon=1e-12):
    return abs(a - b) < epsilon


def get_roots(G, k=4):
    """
    Select root nodes at the geographic corners of the graph.

    If ``X``/``Y`` coordinates are absent, falls back to selecting ``k`` nodes
    evenly spread across the GEOID20-sorted node order (which approximates
    geographic spread for census geographies).

    Parameters
    ----------
    G : networkx.Graph
        Graph with ``X``, ``Y`` attributes on nodes (or ``GEOID20`` for fallback).
    k : {2, 4}
        Number of corners. ``4`` returns [NE, SE, NW, SW];
        ``2`` returns [SE, NW].

    Returns
    -------
    list
        Node identifiers of the selected corners.

    Raises
    ------
    ValueError
        If ``k`` is not 4.
    """

    NE_val = max(_x(G, i) + _y(G, i) for i in G.nodes)
    SE_val = max(_x(G, i) - _y(G, i) for i in G.nodes)
    NW_val = max(-_x(G, i) + _y(G, i) for i in G.nodes)
    SW_val = max(-_x(G, i) - _y(G, i) for i in G.nodes)

    NE = [i for i in G.nodes if _equals(_x(G, i) + _y(G, i), NE_val)][0]
    SE = [i for i in G.nodes if _equals(_x(G, i) - _y(G, i), SE_val)][0]
    NW = [i for i in G.nodes if _equals(-_x(G, i) + _y(G, i), NW_val)][0]
    SW = [i for i in G.nodes if _equals(-_x(G, i) - _y(G, i), SW_val)][0]

    if k == 4:
        return [NE, SE, NW, SW]
    else:
        raise ValueError(f"Only k=2 or k=4, got k={k}")


def sq_eucl_dist_to_point(G, i, cx, cy):
    """
    Squared distance from node i to an arbitrary point.

    Parameters
    ----------
    G : networkx.Graph
        Graph with ``C_X``, ``C_Y`` attributes on nodes.
    i : node
        Node identifier.
    cx, cy : float
        Target longitude and latitude.

    Returns
    -------
    float
        Squared Euclidean distance.
    """

    return (G.nodes[i]["C_X"] - cx) ** 2 + (G.nodes[i]["C_Y"] - cy) ** 2


def nearest_node(G, district, cx, cy):
    """
    Find the node in a district closest to a geographic point.

    Parameters
    ----------
    G : networkx.Graph
        Graph with ``C_X``, ``C_Y`` attributes on nodes.
    district : iterable
        Node identifiers to search within.
    cx, cy : float
        Target longitude and latitude.

    Returns
    -------
    node
        Closest node identifier.
    """
    return min(district, key=lambda i: sq_eucl_dist_to_point(G, i, cx, cy))


def two_sweep(G):
    """
    Approximate the Euclidean diameter of the graph's point set using two-sweep.

    Parameters
    ----------
    G : networkx.Graph
        Graph with ``X``, ``Y`` attributes on nodes.

    Returns
    -------
    float
        Approximate diameter (Euclidean distance between the two farthest points found).
    """
    v1 = next(iter(G.nodes))
    v2 = max(G.nodes, key=lambda i: squared_euclidean_distance(G, v1, i))
    v3 = max(G.nodes, key=lambda i: squared_euclidean_distance(G, v2, i))
    return 2 * euclidean_distance(G, v2, v3)


def set_hop_M_weights(G):
    """
    Set hierarchical hop-M edge weights based on GEOID20 county/tract membership.

    M = number of nodes. Edge weight is:
      - 1            if endpoints share the same tract  (GEOID20[:11] match)
      - 1 + M        if same county, different tract    (GEOID20[:5] match)
      - 1 + M²       if different county

    Parameters
    ----------
    G : networkx.Graph
        Graph with ``GEOID20`` attribute on nodes.
    """
    M = G.number_of_nodes()
    M_sq = M * M
    for i, j in G.edges:
        gi = G.nodes[i]["GEOID20"]
        gj = G.nodes[j]["GEOID20"]
        if gi[:11] == gj[:11]:
            G.edges[i, j]["weight"] = 1
        elif gi[:5] == gj[:5]:
            G.edges[i, j]["weight"] = 1 + M
        else:
            G.edges[i, j]["weight"] = 1 + M_sq


def set_euclidean_M_weights(G):
    """
    Set hierarchical Euclidean-M edge weights based on GEOID20 county/tract membership.

    M = two-sweep approximate diameter. Edge weight is:
      - eucl(i,j)        if endpoints share the same tract  (GEOID20[:11] match)
      - eucl(i,j) + M    if same county, different tract    (GEOID20[:5] match)
      - eucl(i,j) + M²   if different county

    Parameters
    ----------
    G : networkx.Graph
        Graph with ``X``, ``Y``, ``GEOID20`` attributes on nodes.
    """
    M = two_sweep(G)
    M_sq = M * M
    for i, j in G.edges:
        gi = G.nodes[i]["GEOID20"]
        gj = G.nodes[j]["GEOID20"]
        base = euclidean_distance(G, i, j)
        if gi[:11] == gj[:11]:
            G.edges[i, j]["weight"] = base
        elif gi[:5] == gj[:5]:
            G.edges[i, j]["weight"] = base + M
        else:
            G.edges[i, j]["weight"] = base + M_sq


def make_grid_graph(nrows, ncols):
    """
    Build a grid graph with integer node IDs and unit populations.

    Parameters
    ----------
    nrows, ncols : int
        Grid dimensions.

    Returns
    -------
    networkx.Graph
        Grid graph with ``TOTPOP=1``, ``X``, ``Y`` on each node.
    """
    G = nx.grid_2d_graph(nrows, ncols)
    mapping = dict(zip(G, range(nrows * ncols)))
    G = nx.relabel_nodes(G, mapping)
    for i in G.nodes:
        row, col = divmod(i, ncols)
        G.nodes[i]["TOTPOP"] = 1
        G.nodes[i]["X"] = float(col)
        G.nodes[i]["Y"] = float(row)
    return G

def make_trigrid_graph(nrows, ncols):
    """
    Build a grid graph with integer node IDs and unit populations.

    Parameters
    ----------
    nrows, ncols : int
        Grid dimensions.

    Returns
    -------
    networkx.Graph
        Grid graph with ``TOTPOP=1``, ``X``, ``Y`` on each node.
    """
    m = nrows-1
    n = 2 * (ncols-1)
    G = nx.triangular_lattice_graph(m, n)
    mapping = dict(zip(G, range(nrows*ncols)))
    G = nx.relabel_nodes(G, mapping)
    for i in G.nodes:
        row, col = divmod(i, ncols)
        hor_offset = 0.5 if row % 2 else 0
        vert_scaling = math.sqrt(2)
        G.nodes[i]["TOTPOP"] = 1
        G.nodes[i]["X"] = float(col) + hor_offset
        G.nodes[i]["Y"] = float(row) * vert_scaling
    return G
