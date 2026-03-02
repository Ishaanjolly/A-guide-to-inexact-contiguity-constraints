import networkx as nx
import gurobipy as gp
from gurobipy import GRB


def find_minimal_separator(DG, component, b):
    """
    Find a minimal separator between a component and vertex b in a directed graph.

    This function finds a minimal set of vertices that separate a given component
    from a target vertex b. It works by:
    1. Finding the boundary nodes of the component
    2. Running a BFS from b and marking visited nodes
    3. Returning boundary nodes that are reachable from b

    Args:
        DG: NetworkX DiGraph
        component: Set of vertices forming a component
        b: Target vertex to separate from the component

    Returns:
        List of vertices forming a minimal separator between component and b
    """
    # Track boundary nodes of the component
    neighbors_component = {i: False for i in DG.nodes}
    for i in nx.node_boundary(DG, component, None):
        neighbors_component[i] = True

    # BFS from b to find reachable nodes
    visited = {i: False for i in DG.nodes}
    child = [b]
    visited[b] = True

    while child:
        parent = child
        child = list()
        for i in parent:
            if not neighbors_component[i]:
                for j in DG.neighbors(i):
                    if not visited[j]:
                        child.append(j)
                        visited[j] = True

    # Return boundary nodes that are reachable from b
    return [i for i in DG.nodes if neighbors_component[i] and visited[i]]


def minimal_length_U_separator(DG, a, b, C):
    """
    Find a minimal subset of C that forms a length-U a,b-separator.

    A length-U a,b-separator is a set of vertices C such that the shortest
    path from a to b in G-C has total population weight > U. This function
    finds a minimal such set by iteratively trying to remove vertices from C
    while maintaining the separator property.

    Args:
        DG: NetworkX DiGraph with node attribute 'TOTPOP' and graph attribute '_U'
        a: Source vertex
        b: Target vertex
        C: Initial set of vertices forming a length-U a,b-separator

    Returns:
        List of vertices forming a minimal length-U a,b-separator
    """
    for u, v in DG.edges():
        DG[u][v]["lcutweight"] = DG.nodes[u]["TOTPOP"]

    # "remove" C from graph by setting outgoing edge weights to infinity
    for c in C:
        for node in DG.neighbors(c):
            DG[c][node]["lcutweight"] = DG._U + 1

    # is C\{c} a length-U a,b-separator still? If so, remove c from C
    drop_from_C = list()
    for c in C:
        # temporarily add c back (i.e., "remove" c from the cut C)
        for node in DG.neighbors(c):
            DG[c][node]["lcutweight"] = DG.nodes[c]["TOTPOP"]

        distance_from_a = nx.single_source_dijkstra_path_length(
            DG, a, weight="lcutweight"
        )

        if distance_from_a[b] + DG.nodes[b]["TOTPOP"] > DG._U:
            # c was not needed — drop it
            drop_from_C.append(c)
        else:
            # keep c in C; revert its outgoing weights back to infinity
            for node in DG.neighbors(c):
                DG[c][node]["lcutweight"] = DG._U + 1

    return [c for c in C if c not in drop_from_C]


def single_district_cut_callback(m, where):
    """Gurobi callback enforcing single‑district contiguity via cuts.

    When a feasible solution is foundthe routine examines each strongly
    connected component of the subgraph induced by vertices assigned to the
    district and adds a lazy cut if a component is disconnected from the
    root.

    Args:
        m (gurobipy.Model): optimization model.
        where (int): callback context.
    """
    if where != GRB.Callback.MIPSOL:
        return

    m._numCallbacks += 1
    DG = m._DG
    xval = m.cbGetSolution(m._x)

    # Vertices assigned to this district
    S = [v for v in DG.nodes if xval[v] > 0.5]
    b = m._root

    # For each component that doesn't contain root, add a cut
    for component in nx.strongly_connected_components(DG.subgraph(S)):
        if b in component:
            continue

        maxp = max(DG.nodes[v]["TOTPOP"] for v in component)
        a = [v for v in component if DG.nodes[v]["TOTPOP"] == maxp][0]

        C = find_minimal_separator(DG, component, b)

        if m._contiguity == "lcut":
            C = minimal_length_U_separator(DG, a, b, C)

        m.cbLazy(m._x[a] + m._x[b] <= 1 + gp.quicksum(m._x[c] for c in C))
        m._numLazyCuts += 1


def multi_district_cut_callback(m, where):
    """Gurobi callback enforcing multi‑district contiguity via cuts.

    Similar to Single_district_cut_callback but iterates over multiple
    districts stored in m._k and a list of roots m._roots.

    Args:
        m (gurobipy.Model): optimization model.
        where (int): callback context.
    """
    if where != GRB.Callback.MIPSOL:
        return

    m._numCallbacks += 1
    DG = m._DG
    k = m._k
    xval = m.cbGetSolution(m._x)

    for j in range(k):
        S = [v for v in DG.nodes if xval[v, j] > 0.5]
        b = m._roots[j]

        for component in nx.strongly_connected_components(DG.subgraph(S)):
            if b in component:
                continue

            maxp = max(DG.nodes[v]["TOTPOP"] for v in component)
            a = [v for v in component if DG.nodes[v]["TOTPOP"] == maxp][0]

            C = find_minimal_separator(DG, component, b)

            if m._contiguity == "lcut":
                C = minimal_length_U_separator(DG, a, b, C)

            m.cbLazy(m._x[a, j] + m._x[b, j] <= 1 + gp.quicksum(m._x[c, j] for c in C))
            m._numLazyCuts += 1
