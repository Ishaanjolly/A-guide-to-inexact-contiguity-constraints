import math
import networkx as nx


def euclidean_distance(G, i, j, coord_type="geographic"):
    """
    Compute Euclidean distance between nodes i and j.

    Args:
        G: NetworkX graph with node coordinates
        i, j: Node identifiers
        coord_type: 'geographic' uses C_X, C_Y (degrees lon/lat)
                    'projected'  uses X, Y (km, after update_attributes)
    """
    if coord_type == "geographic":
        dx = G.nodes[i]["C_X"] - G.nodes[j]["C_X"]
        dy = G.nodes[i]["C_Y"] - G.nodes[j]["C_Y"]
    else:
        dx = G.nodes[i]["X"] - G.nodes[j]["X"]
        dy = G.nodes[i]["Y"] - G.nodes[j]["Y"]
    return math.sqrt(dx * dx + dy * dy)


def set_euclidean_weights(G):
    """
    Set the 'weight' attribute on every edge to the Euclidean distance
    between the two endpoint centroids (C_X, C_Y).

    Must be called after C_X and C_Y are present on all nodes (i.e. after
    update_attributes or read_graph_from_json).  The weighted contiguity
    methods (tree/dist/dag with use_weighted_distances=True) and the
    weighted_moi objective both consume this 'weight' attribute.
    """
    for i, j in G.edges:
        G.edges[i, j]["weight"] = euclidean_distance(G, i, j)


def _x(G, i):
    return G.nodes[i]["X"]


def _y(G, i):
    return G.nodes[i]["Y"]


def _equals(a, b, epsilon=1e-12):
    return abs(a - b) < epsilon


def select_corners(G, k=4):
    """
    Select k root nodes at the geographic corners of the graph using
    diagonal projections on projected (X, Y) coordinates.

    k=4 returns [NE, SE, NW, SW].
    k=2 returns [SE, NW] (east–west axis).

    Requires X, Y attributes on nodes (call update_attributes first).
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
    elif k == 2:
        return [SE, NW]
    else:
        raise ValueError(f"select_corners supports k=2 or k=4, got k={k}")


def select_roots_east_west(G):
    """
    Select the westernmost and easternmost nodes using geographic C_X coordinates.

    Returns:
        [west_node, east_node]
    """
    x_coords = {i: G.nodes[i]["C_X"] for i in G.nodes}
    return [min(x_coords, key=x_coords.get), max(x_coords, key=x_coords.get)]


def select_roots_north_south(G):
    """
    Select the southernmost and northernmost nodes using geographic C_Y coordinates.

    Returns:
        [south_node, north_node]
    """
    y_coords = {i: G.nodes[i]["C_Y"] for i in G.nodes}
    return [min(y_coords, key=y_coords.get), max(y_coords, key=y_coords.get)]


def get_roots(G, k, root_strategy="corner"):
    """
    Select k root nodes for the MIP model.

    Args:
        G: NetworkX graph with node attributes set by update_attributes
        k: Number of roots (districts)
        root_strategy: 'corner'      — diagonal corner projection, k=2 or k=4
                       'east_west'   — westernmost + easternmost, k=2 only
                       'north_south' — southernmost + northernmost, k=2 only

    Returns:
        List of k node identifiers
    """
    if root_strategy == "corner":
        return select_corners(G, k=k)
    elif root_strategy == "east_west":
        if k != 2:
            raise ValueError("east_west root strategy requires k=2")
        return select_roots_east_west(G)
    elif root_strategy == "north_south":
        if k != 2:
            raise ValueError("north_south root strategy requires k=2")
        return select_roots_north_south(G)
    else:
        raise ValueError(
            f"Unknown root_strategy: '{root_strategy}'. "
            f"Choose from 'corner', 'east_west', or 'north_south'."
        )


def sq_eucl_dist_to_point(G, i, cx, cy):
    """
    Squared geographic distance from node i to an arbitrary point (cx, cy).

    Args:
        G: NetworkX graph with C_X, C_Y on nodes
        i: Node identifier
        cx, cy: Target longitude and latitude

    Returns:
        Squared Euclidean distance (no sqrt — only used for comparisons)
    """
    return (G.nodes[i]["C_X"] - cx) ** 2 + (G.nodes[i]["C_Y"] - cy) ** 2


def nearest_node(G, district, cx, cy):
    """
    Find the node in `district` closest to geographic point (cx, cy).

    Useful for assigning a root to an existing district polygon centroid.

    Args:
        G: NetworkX graph with C_X, C_Y on nodes
        district: Iterable of node identifiers
        cx, cy: Target longitude and latitude

    Returns:
        Node identifier of the closest node in district
    """
    return min(district, key=lambda i: sq_eucl_dist_to_point(G, i, cx, cy))


def make_grid_graph(nrows, ncols):
    """Build an nrows×ncols grid graph with integer node IDs and TOTPOP=1."""
    G = nx.grid_2d_graph(nrows, ncols)
    mapping = dict(zip(G, range(nrows * ncols)))
    G = nx.relabel_nodes(G, mapping)
    for i in G.nodes:
        row, col = divmod(i, ncols)
        G.nodes[i]["TOTPOP"] = 1
        G.nodes[i]["X"] = float(col)
        G.nodes[i]["Y"] = float(row)
    return G
