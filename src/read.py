import json
from networkx.readwrite import json_graph
from pyproj import Proj
from src.params import BaseParams


def read_graph_from_json(
    json_file, state=None, update_population=True, rescale_distance=True
):
    """
    Reads a graph from a JSON adjacency file and optionally enriches node attributes.

    Args:
        json_file (str): Path to the JSON file in NetworkX adjacency format.
        state (str or None): Two-letter state abbreviation (e.g. ``'IA'``).
            When provided, sets ``C_X``/``C_Y`` (geographic centroid in
            degrees), ``X``/``Y`` (projected centroid in km), and ``TOTPOP``
            on every node. When ``None``, projection is skipped.
        update_population (bool): If ``True``, sets ``TOTPOP = P0010001`` on
            every node. Ignored when ``state`` is provided. Defaults to
            ``True``.
        rescale_distance (bool): If ``True``, divides ``area``,
            ``boundary_perim``, and ``shared_perim`` by 100,000 to convert
            metres to ~100 km units for better Gurobi conditioning. Defaults
            to ``True``.

    Returns:
        networkx.Graph: The loaded graph with enriched node attributes.
    """
    with open(json_file) as f:
        data = json.load(f)

    G = json_graph.adjacency_graph(data)

    if state is not None:
        epsg = BaseParams().state_epsg_mapping[state]["epsg"]
        proj = Proj(f"EPSG:{epsg}", preserve_units=True)
        for i in G.nodes:
            G.nodes[i]["C_X"] = float(G.nodes[i]["INTPTLON20"])
            G.nodes[i]["C_Y"] = float(G.nodes[i]["INTPTLAT20"])
            G.nodes[i]["TOTPOP"] = int(G.nodes[i]["P0010001"])
            x_m, y_m = proj(G.nodes[i]["C_X"], G.nodes[i]["C_Y"])
            G.nodes[i]["X"] = x_m / 1000  # meters to km
            G.nodes[i]["Y"] = y_m / 1000

    elif update_population:
        for i in G.nodes:
            G.nodes[i]["TOTPOP"] = G.nodes[i]["P0010001"]

    if rescale_distance:
        ht = 100000
        for i in G.nodes:
            G.nodes[i]["area"] /= ht * ht
            if G.nodes[i]["boundary_node"]:
                G.nodes[i]["boundary_perim"] /= ht
        for i, j in G.edges:
            G.edges[i, j]["shared_perim"] /= ht

    return G
