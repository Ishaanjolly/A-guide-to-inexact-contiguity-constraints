import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import networkx as nx


def draw_district(filepath, filename, G, district, state=None, level=None, zoom=False):
    """Draws a single district or cluster of nodes on a choropleth map.

    Reads a shapefile and colours nodes belonging to the given district.
    Matches graph nodes to shapefile rows via the GEOID20 identifier.

    Args:
        filepath: Path to the directory containing the shapefile.
        filename: Shapefile filename.
        G: NetworkX graph with GEOID20 node attributes.
        district: Iterable of node IDs to highlight.
        state: State label used in the plot title. Defaults to None.
        level: Level label used in the plot title. Defaults to None.
        zoom: If True, unselected nodes are set to None instead of False,
            enabling zoom-friendly rendering. Defaults to False.
    """
    if filepath + filename is None:
        raise ValueError("Filepath and filename must be provided to draw district.")

    df = gpd.read_file(filepath + filename)

    node_with_this_geoid = {G.nodes[i]["GEOID20"]: i for i in G.nodes}
    assignment = [-1 for i in G.nodes]

    if zoom:
        picked = {i: None for i in G.nodes}
    else:
        picked = {i: False for i in G.nodes}

    for i in district:
        picked[i] = True

    for u in range(G.number_of_nodes()):
        geoid = df["GEOID20"][u]
        i = node_with_this_geoid[geoid]
        assignment[u] = picked[i]

    df["assignment"] = assignment
    df.plot(column="assignment").get_figure()
    if state is not None and level is not None:
        plt.title(str(state) + "-" + str(level))


def draw_plan(
    filepath,
    filename,
    G,
    plan,
    state=None,
    level=None,
):
    """Draws a full districting plan with each district in a distinct colour.

    Reads a shapefile and assigns each node a district label based on its
    position in the plan. Matches graph nodes to shapefile rows via GEOID20.

    Args:
        filepath: Path to the directory containing the shapefile.
        filename: Shapefile filename.
        G: NetworkX graph with GEOID20 node attributes.
        plan: List of sets/lists where plan[j] contains node IDs for district j.
        state: State label used in the plot title. Defaults to None.
        level: Level label used in the plot title. Defaults to None.
    """

    df = gpd.read_file(filepath + filename)
    assignment = [-1 for i in G.nodes]
    labeling = {i: j for j in range(len(plan)) for i in plan[j]}
    node_with_this_geoid = {G.nodes[i]["GEOID20"]: i for i in G.nodes}

    for u in range(G.number_of_nodes()):
        geoid = df["GEOID20"][u]
        i = node_with_this_geoid[geoid]
        assignment[u] = labeling[i]

    df["assignment"] = assignment
    df.plot(column="assignment").get_figure()
    if state is not None and level is not None:
        plt.title(str(state) + "-" + str(level))


def visualize_roots(G, roots, title="Root Node Locations", figsize=(12, 10)):
    """Plots graph nodes with root nodes highlighted as red stars.

    Uses X and Y (km) coordinates set by update_attributes().

    Args:
        G: NetworkX graph with X and Y node attributes.
        roots: Iterable of root node IDs to highlight.
        title: Plot title. Defaults to "Root Node Locations".
        figsize: Figure dimensions as (width, height). Defaults to (12, 10).

    Returns:
        matplotlib.figure.Figure: The generated figure.
    """
    fig, ax = plt.subplots(figsize=figsize)

    xs = [G.nodes[i]["X"] for i in G.nodes]
    ys = [G.nodes[i]["Y"] for i in G.nodes]
    ax.scatter(xs, ys, c="blue", s=50, zorder=1)

    root_xs = [G.nodes[r]["X"] for r in roots]
    root_ys = [G.nodes[r]["Y"] for r in roots]
    ax.scatter(root_xs, root_ys, c="red", marker="*", s=200, zorder=2, label="Roots")

    ax.set_title(title)
    ax.legend()
    plt.tight_layout()
    return fig


def visualize_roots_with_districts(
    G, roots, districts=None, title="Districts with Roots", figsize=(12, 10)
):
    """Plots nodes colour-coded by district with root nodes marked as red stars.

    Uses X and Y (km) coordinates set by update_attributes(). Each root node
    is annotated with its district index.

    Args:
        G: NetworkX graph with X and Y node attributes.
        roots: List of root node IDs, one per district.
        districts: List of sets/lists where districts[j] contains node IDs for
            district j. If None, all nodes are plotted in uniform lightblue.
            Defaults to None.
        title: Plot title. Defaults to "Districts with Roots".
        figsize: Figure dimensions as (width, height). Defaults to (12, 10).

    Returns:
        matplotlib.figure.Figure: The generated figure.
    """
    fig, ax = plt.subplots(figsize=figsize)
    cmap = plt.cm.get_cmap("tab20", max(len(roots), 1))

    if districts is not None:
        labeling = {i: j for j, d in enumerate(districts) for i in d}
        xs = np.array([G.nodes[i]["X"] for i in G.nodes])
        ys = np.array([G.nodes[i]["Y"] for i in G.nodes])
        colors = np.array([labeling.get(i, -1) for i in G.nodes])
        ax.scatter(xs, ys, c=colors, cmap=cmap, s=50, zorder=1)
    else:
        xs = [G.nodes[i]["X"] for i in G.nodes]
        ys = [G.nodes[i]["Y"] for i in G.nodes]
        ax.scatter(xs, ys, c="blue", s=50, zorder=1)

    root_xs = [G.nodes[r]["X"] for r in roots]
    root_ys = [G.nodes[r]["Y"] for r in roots]
    ax.scatter(root_xs, root_ys, c="red", marker="*", s=200, zorder=2, label="Roots")

    for j, r in enumerate(roots):
        ax.annotate(
            str(j),
            (G.nodes[r]["X"], G.nodes[r]["Y"]),
            fontsize=8,
            ha="center",
            va="bottom",
            zorder=3,
        )

    ax.set_title(title)
    ax.legend()
    plt.tight_layout()
    return fig


def make_triangular_lattice(width):
    """Creates a triangular lattice graph with unit population at each node.

    Constructs an (width-1) x 2*(width-1) triangular lattice, assigns unit
    population to each node, and relabels nodes to sequential integers.

    Args:
        width: Controls grid dimensions; produces (width-1) rows and
            2*(width-1) columns.

    Returns:
        networkx.Graph: Relabelled triangular lattice graph with TOTPOP=1
            and pos attributes on each node.
    """
    nrows = width - 1
    ncols = 2 * (width - 1)
    G = nx.triangular_lattice_graph(nrows, ncols)
    for v in G.nodes:
        G.nodes[v]["TOTPOP"] = 1
    mapping = dict(zip(G, range(nrows * ncols)))
    G = nx.relabel_nodes(G, mapping)
    return G


def make_grid(width):
    """Creates a square grid graph with unit population at each node.

    Constructs a width x width 2D grid graph, assigns unit population and
    X/Y coordinate attributes to each node, then relabels nodes to sequential
    integers.

    Args:
        width: Number of rows and columns in the grid.

    Returns:
        networkx.Graph: Relabelled grid graph with TOTPOP=1, X, and Y
            attributes on each node.
    """
    G = nx.grid_2d_graph(width, width)
    for i, j in G.nodes:
        G.nodes[i, j]["TOTPOP"] = 1
        G.nodes[i, j]["X"] = i
        G.nodes[i, j]["Y"] = j
    mapping = dict(zip(G, range(width * width)))
    G = nx.relabel_nodes(G, mapping)
    return G


def draw_graph(G, graph_type="grid", with_labels=True):
    """Draws a graph using node position attributes.

    Args:
        G: NetworkX graph with positional attributes.
        graph_type: Either 'grid' (uses X, Y attributes) or 'triangular'
            (uses pos attribute). Defaults to 'grid'.
    """
    if graph_type == "grid":
        pos = {i: (G.nodes[i]["X"], G.nodes[i]["Y"]) for i in G.nodes}
    elif graph_type == "triangular":
        pos = {i: G.nodes[i]["pos"] for i in G.nodes}
    nx.draw(G, pos=pos, with_labels=with_labels)
