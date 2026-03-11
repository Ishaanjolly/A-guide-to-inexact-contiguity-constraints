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

    Parameters
    ----------
    G : networkx.Graph
        Graph with ``X``, ``Y`` attributes on nodes.
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
