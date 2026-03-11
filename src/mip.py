"""
MIP for solving Single and Multi-distriting problems with various contiguity and objective options.

Authors: Ishaan Jolly and Austin Buchanan
"""

import networkx as nx
import gurobipy as gp
from gurobipy import GRB
import math
import os
from src.utils import squared_euclidean_distance
from src.mip_utils import (
    single_district_cut_callback,
    multi_district_cut_callback,
)

VALID_CONTIGUITY = {None, "tree", "dist", "dag", "shir", "cut", "lcut"}
VALID_OBJECTIVES = {
    None,
    "cut_edges",
    "shared_perim",
    "perim",
    "inverse_polsby_popper",
    "hop_moi",
    "weighted_moi",
    "euclidean_moi",
}


class DistrictingModel:
    """Base class for districting optimization models."""

    VALID_CONTIGUITY = VALID_CONTIGUITY
    VALID_OBJECTIVES = VALID_OBJECTIVES

    def __init__(
        self,
        G,
        k,
        deviation_persons,
        roots,
        contiguity=None,
        objective=None,
        use_weighted_distances=False,
        ideal_population=None,
        verbose=True,
    ):
        self.G = G
        self.DG = nx.DiGraph(G)
        self.k = k
        self.deviation_persons = deviation_persons
        self.roots = roots if isinstance(roots, list) else [roots]
        self.contiguity = contiguity
        self.objective = objective
        self.use_weighted_distances = use_weighted_distances
        self.verbose = verbose

        if ideal_population is None:
            ideal_population = (
                sum(self.DG.nodes[i]["TOTPOP"] for i in self.DG.nodes) / k
            )
        self.DG._L = math.ceil(ideal_population - deviation_persons)
        self.DG._U = math.floor(ideal_population + deviation_persons)

        if self.verbose:
            print("Using L, U, k =", self.DG._L, self.DG._U, k)

        self.model = gp.Model()
        self.model.Params.OutputFlag = 1
        self.model.Params.LogToConsole = 1
        self.model._numCallbacks = 0
        self.model._numLazyCuts = 0
        self.model._callback = None

        self._validate()

    def _validate(self):
        """Validate all inputs."""
        if not all(root in self.DG.nodes for root in self.roots):
            raise ValueError("All roots must be valid nodes in the graph.")
        if self.contiguity not in self.VALID_CONTIGUITY:
            raise ValueError(f"Invalid contiguity: {self.contiguity}")
        if self.objective not in self.VALID_OBJECTIVES:
            raise ValueError(f"Invalid objective: {self.objective}")

    def _validate_pool(self, pool_search, pool_size):
        """Validate pool search parameters."""
        if pool_search not in {0, 1, 2}:
            raise ValueError("pool_search must be one of {0, 1, 2}")
        if pool_size <= 0:
            raise ValueError("pool_size must be greater than 0")
        if pool_search > 0 and self.contiguity == "shir":
            raise ValueError(
                "Cannot use shirabe contiguity ('shir') when pool_search > 0"
            )

    def _get_predecessors(self, root):
        """Get BFS or Dijkstra predecessors and distances from root."""
        if self.use_weighted_distances:
            pred, dist = nx.dijkstra_predecessor_and_distance(
                self.DG, source=root, weight="weight"
            )
        else:
            pred = nx.predecessor(self.DG, source=root)
            dist = nx.single_source_shortest_path_length(self.DG, source=root)
        return pred, dist

    def _setup_objective(self):
        """Dispatch to the appropriate objective setup."""
        if self.objective in {"hop_moi", "weighted_moi", "euclidean_moi"}:
            self._setup_moi_objective()
        elif self.objective == "cut_edges":
            self._setup_cut_edges_objective()
        elif self.objective == "shared_perim":
            self._setup_shared_perim_objective()
        elif self.objective == "perim":
            self._setup_perim_objective()
        elif self.objective == "inverse_polsby_popper":
            self._setup_polsby_popper_objective()

    def _add_contiguity_constraints(self):
        """Dispatch to the appropriate contiguity method."""
        if self.contiguity == "tree":
            self._add_tree_contiguity()
        elif self.contiguity == "dist":
            self._add_dist_contiguity()
        elif self.contiguity == "dag":
            self._add_dag_contiguity()
        elif self.contiguity == "shir":
            self._add_shirabe_contiguity()
        elif self.contiguity in {"cut", "lcut"}:
            self._add_cut_contiguity()

    def _add_cut_contiguity(self):
        """Shared cut-contiguity setup (enables lazy constraints)."""
        self.model.Params.LazyConstraints = 1
        self.model._DG = self.DG
        self.model._contiguity = self.contiguity

    def build(self, pool_search=0, pool_size=1):
        """Assemble the full MIP model."""
        self._validate_pool(pool_search, pool_size)
        self._create_variables()
        self._add_assignment_constraints()
        self._add_population_constraints()
        self._add_cut_edge_constraints(pool_search=pool_search)
        self._setup_objective()
        self._add_contiguity_constraints()
        self.model.update()

    def solve(
        self,
        time_limit=3600,
        pool_search=0,
        pool_size=1,
        cutoff=None,
        log_file=None,
        model_file=None,
    ):
        """Solve the model and return a metrics dictionary."""
        os.makedirs("logs", exist_ok=True)
        os.makedirs("models", exist_ok=True)

        self._validate_pool(pool_search, pool_size)

        self.model.Params.MIPGap = 0.00
        self.model.Params.PoolSearchMode = pool_search
        self.model.Params.PoolSolutions = pool_size
        self.model.Params.TimeLimit = time_limit

        if cutoff is not None:
            self.model.Params.Cutoff = cutoff
        if log_file is not None:
            self.model.Params.LogFile = log_file
        if model_file is not None:
            self.model.write(model_file)

        self.model.update()
        self.model.optimize(self.model._callback)

        return self._build_metrics()

    def _build_metrics(self):
        """Build the metrics dictionary from the solved model."""
        status_map = {
            GRB.OPTIMAL: "Optimal",
            GRB.INFEASIBLE: "Infeasible",
            GRB.TIME_LIMIT: "Time Limit",
            GRB.CUTOFF: "Cutoff",
            GRB.UNBOUNDED: "Unbounded",
            GRB.INF_OR_UNBD: "Infeasible or Unbounded",
            GRB.NODE_LIMIT: "Node Limit",
            GRB.SOLUTION_LIMIT: "Solution Limit",
            GRB.INTERRUPTED: "Interrupted",
        }

        return {
            "time_best": self.model.Runtime,
            "objective_type": self.objective,
            "objective": self.model.ObjVal if self.model.SolCount > 0 else None,
            "obj_bound": self.model.ObjBound if self.model.SolCount > 0 else None,
            "obj_gap": self.model.MIPGap if self.model.SolCount > 0 else None,
            "nonzeros": self.model.NumNZs,
            "num_solutions": self.model.SolCount,
            "status": status_map.get(
                self.model.Status, f"Unknown ({self.model.Status})"
            ),
            "contiguity": self.contiguity,
            "sparsity": (
                1 - (self.model.NumNZs / (self.model.NumConstrs * self.model.NumVars))
            )
            * 100,
            "num_callbacks": self.model._numCallbacks,
            "num_lazy_cuts": self.model._numLazyCuts,
        }


class SingleDistrictModel(DistrictingModel):
    """Model for finding a single optimal district."""

    def __init__(self, G, k, deviation_persons, root=None, **kwargs):
        if root is None:
            maxp = max(G.nodes[i]["TOTPOP"] for i in G.nodes)
            root = [i for i in G.nodes if G.nodes[i]["TOTPOP"] == maxp][0]
        super().__init__(G, k, deviation_persons, roots=[root], **kwargs)
        self.root = self.roots[0]

    def _create_variables(self):
        self.model._x = self.model.addVars(self.DG.nodes, name="x", vtype=GRB.BINARY)
        self.model._x[self.root].LB = 1

        if self.objective not in {None, "hop_moi", "weighted_moi", "euclidean_moi"}:
            self.model._y = self.model.addVars(
                self.DG.edges, name="y", vtype=GRB.BINARY
            )

    def _add_assignment_constraints(self):
        pass  # no assignment constraints for a single district

    def _add_population_constraints(self):
        if self.deviation_persons is not None:
            self.model.addConstr(
                gp.sum(
                    self.DG.nodes[i]["TOTPOP"] * self.model._x[i] for i in self.DG.nodes
                )
                >= self.DG._L
            )
            self.model.addConstr(
                gp.sum(
                    self.DG.nodes[i]["TOTPOP"] * self.model._x[i] for i in self.DG.nodes
                )
                <= self.DG._U
            )

    def _add_cut_edge_constraints(self, pool_search=0):
        if self.objective in {None, "hop_moi", "weighted_moi", "euclidean_moi"}:
            return
        self.model.addConstrs(
            self.model._x[u] - self.model._x[v] <= self.model._y[u, v]
            for u, v in self.DG.edges
        )
        if pool_search > 0:
            self.model.addConstrs(
                self.model._y[u, v] <= self.model._x[u] for u, v in self.DG.edges
            )
            self.model.addConstrs(
                self.model._x[v] + self.model._y[u, v] <= 1 for u, v in self.DG.edges
            )

    def _setup_moi_objective(self):
        if self.objective == "hop_moi":
            dist = nx.single_source_shortest_path_length(self.DG, source=self.root)
            self.model.setObjective(
                gp.sum(
                    dist[i] ** 2 * self.G.nodes[i]["TOTPOP"] * self.model._x[i]
                    for i in self.G.nodes
                ),
                GRB.MINIMIZE,
            )
        elif self.objective == "weighted_moi":
            dist = nx.single_source_dijkstra_path_length(
                self.DG, source=self.root, weight="weight"
            )
            self.model.setObjective(
                gp.sum(
                    dist[i] ** 2 * self.G.nodes[i]["TOTPOP"] * self.model._x[i]
                    for i in self.G.nodes
                ),
                GRB.MINIMIZE,
            )
        elif self.objective == "euclidean_moi":
            self.model.setObjective(
                gp.sum(
                    squared_euclidean_distance(self.G, i, self.root)
                    * self.G.nodes[i]["TOTPOP"]
                    * self.model._x[i]
                    for i in self.G.nodes
                ),
                GRB.MINIMIZE,
            )

    def _setup_cut_edges_objective(self):
        self.model.setObjective(gp.sum(self.model._y), GRB.MINIMIZE)

    def _setup_shared_perim_objective(self):
        self.model.setObjective(
            gp.sum(
                self.DG.edges[u, v]["shared_perim"] * self.model._y[u, v]
                for u, v in self.DG.edges
            ),
            GRB.MINIMIZE,
        )

    def _setup_perim_objective(self):
        self.model.setObjective(
            gp.sum(
                self.DG.edges[u, v]["shared_perim"] * self.model._y[u, v]
                for u, v in self.DG.edges
            )
            + gp.sum(
                self.DG.nodes[i]["boundary_perim"] * self.model._x[i]
                for i in self.DG.nodes
                if self.DG.nodes[i]["boundary_node"]
            ),
            GRB.MINIMIZE,
        )

    def _setup_polsby_popper_objective(self):
        m = self.model
        m._z = m.addVar(name="z")
        m._A = m.addVar(name="A")
        m._P = m.addVar(name="P")
        m.setObjective(m._z, GRB.MINIMIZE)
        m.addConstr(m._P * m._P <= 4 * math.pi * m._A * m._z)
        m.addConstr(
            m._A == gp.sum(self.DG.nodes[i]["area"] * m._x[i] for i in self.DG.nodes)
        )
        m.addConstr(
            m._P
            == gp.sum(
                self.DG.edges[u, v]["shared_perim"] * m._y[u, v]
                for u, v in self.DG.edges
            )
            + gp.sum(
                self.DG.nodes[i]["boundary_perim"] * m._x[i]
                for i in self.DG.nodes
                if self.DG.nodes[i]["boundary_node"]
            )
        )

    def _add_tree_contiguity(self):
        pred, _ = self._get_predecessors(self.root)
        self.model.addConstrs(
            self.model._x[i] <= self.model._x[pred[i][0]]
            for i in pred
            if i != self.root
        )

    def _add_dist_contiguity(self):
        pred, _ = self._get_predecessors(self.root)
        self.model.addConstrs(
            self.model._x[i] <= gp.sum(self.model._x[t] for t in pred[i])
            for i in self.DG.nodes
            if i != self.root
        )

    def _add_dag_contiguity(self):
        if self.use_weighted_distances:
            dist = nx.single_source_dijkstra_path_length(
                self.DG, source=self.root, weight="weight"
            )
        else:
            dist = nx.single_source_shortest_path_length(self.DG, source=self.root)
        ordering = sorted(dist.items(), key=lambda item: item[1])
        position = {ordering[p][0]: p for p in range(len(ordering))}
        self.model.addConstrs(
            self.model._x[i]
            <= gp.sum(
                self.model._x[t]
                for t in self.DG.neighbors(i)
                if position[t] < position[i]
            )
            for i in self.DG.nodes
            if i != self.root
        )

    def _add_shirabe_contiguity(self):
        m = self.model
        m._f = m.addVars(self.DG.edges, name="f")
        M = self.DG.number_of_nodes() - 1
        m.addConstrs(
            gp.sum(m._f[j, i] - m._f[i, j] for j in self.DG.neighbors(i)) == m._x[i]
            for i in self.DG.nodes
            if i != self.root
        )
        m.addConstrs(
            gp.sum(m._f[j, i] for j in self.DG.neighbors(i)) <= M * m._x[i]
            for i in self.DG.nodes
            if i != self.root
        )

    def _add_cut_contiguity(self):
        super()._add_cut_contiguity()
        self.model._root = self.root
        self.model._callback = single_district_cut_callback

    def _build_metrics(self):
        metrics = super()._build_metrics()
        if self.model.SolCount > 0:
            try:
                metrics["district"] = [
                    i for i in self.G.nodes if self.model._x[i].x > 0.5
                ]
            except Exception:
                metrics["district"] = None
        else:
            metrics["district"] = None
        return metrics


class MultiDistrictModel(DistrictingModel):
    """Model for finding k optimal districts simultaneously."""

    VALID_OBJECTIVES = VALID_OBJECTIVES | {"bottleneck_polsby_popper"}

    def __init__(self, G, k, deviation_persons, roots, **kwargs):
        if len(roots) != k:
            raise ValueError(f"Number of roots must equal k={k}")
        super().__init__(G, k, deviation_persons, roots, **kwargs)

    def _create_variables(self):
        self.model._x = {}
        for node in self.DG.nodes():
            for j in range(self.k):
                self.model._x[node, j] = self.model.addVar(
                    vtype=GRB.BINARY, name=f"x_{node}_{j}"
                )
        for j in range(self.k):
            self.model._x[self.roots[j], j].LB = 1

        if self.objective in {
            "shared_perim",
            "perim",
            "inverse_polsby_popper",
            "cut_edges",
            "bottleneck_polsby_popper",
        }:
            self.model._y = self.model.addVars(
                self.DG.edges, self.k, name="y", vtype=GRB.BINARY
            )

        self.model.update()

    def _add_assignment_constraints(self):
        self.model.addConstrs(
            gp.sum(self.model._x[i, j] for j in range(self.k)) == 1
            for i in self.DG.nodes
        )

    def _add_population_constraints(self):
        for j in range(self.k):
            self.model.addConstr(
                gp.sum(
                    self.DG.nodes[i]["TOTPOP"] * self.model._x[i, j]
                    for i in self.DG.nodes
                )
                >= self.DG._L
            )
            self.model.addConstr(
                gp.sum(
                    self.DG.nodes[i]["TOTPOP"] * self.model._x[i, j]
                    for i in self.DG.nodes
                )
                <= self.DG._U
            )

    def _add_cut_edge_constraints(self, pool_search=0):
        if self.objective not in {
            "shared_perim",
            "perim",
            "inverse_polsby_popper",
            "cut_edges",
            "bottleneck_polsby_popper",
        }:
            return

        m = self.model
        m.addConstrs(
            m._x[u, j] - m._x[v, j] <= m._y[u, v, j]
            for u, v in self.DG.edges
            for j in range(self.k)
        )

        undirected_edges = [(u, v) for u, v in self.DG.edges if u < v]
        m._is_cut = m.addVars(undirected_edges, vtype=GRB.BINARY)
        m.addConstrs(
            m._is_cut[u, v] == gp.sum(m._y[u, v, j] for j in range(self.k))
            for u, v in undirected_edges
        )
        m.addConstrs(
            m._is_cut[u, v] == gp.sum(m._y[v, u, j] for j in range(self.k))
            for u, v in undirected_edges
        )
        self._undirected_edges = undirected_edges

        if pool_search > 0:
            m.addConstrs(
                m._y[u, v, j] <= m._x[u, j]
                for u, v in self.DG.edges
                for j in range(self.k)
            )
            m.addConstrs(
                m._x[v, j] + m._y[u, v, j] <= 1
                for u, v in self.DG.edges
                for j in range(self.k)
            )

    def _setup_moi_objective(self):
        for j in range(self.k):
            root = self.roots[j]
            if self.objective == "hop_moi":
                dist = nx.single_source_shortest_path_length(self.DG, source=root)
                for i in self.DG.nodes:
                    self.model._x[i, j].obj = dist[i] ** 2 * self.G.nodes[i]["TOTPOP"]
            elif self.objective == "weighted_moi":
                dist = nx.single_source_dijkstra_path_length(
                    self.DG, source=root, weight="weight"
                )
                for i in self.DG.nodes:
                    self.model._x[i, j].obj = dist[i] ** 2 * self.G.nodes[i]["TOTPOP"]
            elif self.objective == "euclidean_moi":
                for i in self.DG.nodes:
                    self.model._x[i, j].obj = (
                        squared_euclidean_distance(self.G, i, root)
                        * self.G.nodes[i]["TOTPOP"]
                    )

    def _setup_cut_edges_objective(self):
        self.model.setObjective(gp.sum(self.model._is_cut), GRB.MINIMIZE)

    def _setup_shared_perim_objective(self):
        self.model.setObjective(
            gp.sum(
                self.DG.edges[u, v]["shared_perim"] * self.model._is_cut[u, v]
                for u, v in self._undirected_edges
            ),
            GRB.MINIMIZE,
        )

    def _setup_perim_objective(self):
        self.model.setObjective(
            gp.sum(
                self.DG.edges[u, v]["shared_perim"] * self.model._y[u, v, j]
                for u, v in self.DG.edges
                for j in range(self.k)
            )
            + gp.sum(
                self.DG.nodes[i]["boundary_perim"]
                for i in self.DG.nodes
                if self.DG.nodes[i]["boundary_node"]
            ),
            GRB.MINIMIZE,
        )

    def _setup_polsby_popper_objective(self):
        m = self.model
        m._z = m.addVars(self.k, name="z")
        m._A = m.addVars(self.k, name="A")
        m._P = m.addVars(self.k, name="P")

        if self.objective == "inverse_polsby_popper":
            m.setObjective((1 / self.k) * gp.sum(m._z), GRB.MINIMIZE)
        elif self.objective == "bottleneck_polsby_popper":
            m._worst_z = m.addVar(name="worst_z")
            m.setObjective(m._worst_z, GRB.MINIMIZE)
            m.addConstrs(m._z[j] <= m._worst_z for j in range(self.k))

        m.addConstrs(
            m._P[j] * m._P[j] <= 4 * math.pi * m._A[j] * m._z[j] for j in range(self.k)
        )
        m.addConstrs(
            m._A[j]
            == gp.sum(self.DG.nodes[i]["area"] * m._x[i, j] for i in self.DG.nodes)
            for j in range(self.k)
        )
        m.addConstrs(
            m._P[j]
            == gp.sum(
                self.DG.edges[u, v]["shared_perim"] * m._y[u, v, j]
                for u, v in self.DG.edges
            )
            + gp.sum(
                self.DG.nodes[i]["boundary_perim"] * m._x[i, j]
                for i in self.DG.nodes
                if self.DG.nodes[i]["boundary_node"]
            )
            for j in range(self.k)
        )

    def _add_tree_contiguity(self):
        for j in range(self.k):
            root = self.roots[j]
            pred, _ = self._get_predecessors(root)
            self.model.addConstrs(
                self.model._x[i, j] <= self.model._x[pred[i][0], j]
                for i in self.DG.nodes
                if i != root
            )

    def _add_dist_contiguity(self):
        for j in range(self.k):
            root = self.roots[j]
            pred, _ = self._get_predecessors(root)
            self.model.addConstrs(
                self.model._x[i, j] <= gp.sum(self.model._x[t, j] for t in pred[i])
                for i in self.DG.nodes
                if i != root
            )

    def _add_dag_contiguity(self):
        for j in range(self.k):
            root = self.roots[j]
            if self.use_weighted_distances:
                dist = nx.single_source_dijkstra_path_length(
                    self.DG, source=root, weight="weight"
                )
            else:
                dist = nx.single_source_shortest_path_length(self.DG, source=root)
            ordering = sorted(dist.items(), key=lambda item: item[1])
            position = {ordering[p][0]: p for p in range(len(ordering))}
            self.model.addConstrs(
                self.model._x[i, j]
                <= gp.sum(
                    self.model._x[t, j]
                    for t in self.DG.neighbors(i)
                    if position[t] < position[i]
                )
                for i in self.DG.nodes
                if i != root
            )

    def _add_shirabe_contiguity(self):
        m = self.model
        m._f = m.addVars(self.DG.edges, self.k, name="f")
        M = self.DG.number_of_nodes() - 1
        for j in range(self.k):
            root = self.roots[j]
            m.addConstrs(
                gp.sum(m._f[u, v, j] - m._f[v, u, j] for u in self.DG.neighbors(v))
                == m._x[v, j]
                for v in self.DG.nodes
                if v != root
            )
            m.addConstrs(
                gp.sum(m._f[u, v, j] for u in self.DG.neighbors(v)) <= M * m._x[v, j]
                for v in self.DG.nodes
                if v != root
            )

    def _add_cut_contiguity(self):
        super()._add_cut_contiguity()
        self.model._roots = self.roots
        self.model._k = self.k
        self.model._callback = multi_district_cut_callback

    def _build_metrics(self):
        metrics = super()._build_metrics()
        metrics["roots"] = self.roots
        if self.model.SolCount > 0:
            try:
                metrics["districts"] = [
                    [i for i in self.G.nodes if self.model._x[i, j].x > 0.5]
                    for j in range(self.k)
                ]
            except Exception:
                metrics["districts"] = None
        else:
            metrics["districts"] = None
        return metrics


## =============== CLASS WRAPPERS ==============


def single_district_mip(
    G,
    k,
    deviation_persons,
    root=None,
    contiguity=None,
    objective=None,
    use_weighted_distances=False,
    ideal_population=None,
    verbose=True,
    pool_search=0,
    pool_size=1,
    cutoff=None,
    time_limit=3600,
    log_file=None,
    model_file=None,
):
    """Build and solve a single-district MIP model."""
    model = SingleDistrictModel(
        G,
        k,
        deviation_persons,
        root,
        contiguity=contiguity,
        objective=objective,
        use_weighted_distances=use_weighted_distances,
        ideal_population=ideal_population,
        verbose=verbose,
    )
    model.build(pool_search=pool_search, pool_size=pool_size)
    metrics = model.solve(
        time_limit=time_limit,
        pool_search=pool_search,
        pool_size=pool_size,
        cutoff=cutoff,
        log_file=log_file,
        model_file=model_file,
    )
    return metrics, model.model


def multi_district_mip(
    G,
    k,
    deviation_persons,
    roots,
    contiguity=None,
    objective=None,
    use_weighted_distances=False,
    ideal_population=None,
    verbose=True,
    pool_search=0,
    pool_size=1,
    cutoff=None,
    time_limit=3600,
    log_file=None,
    model_file=None,
):
    """Build and solve a multi-district MIP model."""
    model = MultiDistrictModel(
        G,
        k,
        deviation_persons,
        roots,
        contiguity=contiguity,
        objective=objective,
        use_weighted_distances=use_weighted_distances,
        ideal_population=ideal_population,
        verbose=verbose,
    )
    model.build(pool_search=pool_search, pool_size=pool_size)
    metrics = model.solve(
        time_limit=time_limit,
        pool_search=pool_search,
        pool_size=pool_size,
        cutoff=cutoff,
        log_file=log_file,
        model_file=model_file,
    )
    return metrics, model.model
