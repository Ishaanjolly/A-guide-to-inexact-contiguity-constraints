import networkx as nx
import gurobipy as gp
from gurobipy import GRB
import math
import os

VALID_CONTIGUITY = {None, "tree", "dist", "dag", "shir", "cut", "lcut"}
VALID_OBJECTIVES = {
    None, "cut_edges", "shared_perim", "perim", 
    "inverse_polsby_popper", "hop_moi", "weighted_moi", "euclidean_moi"
}

class DistrictingModel:
    """Base class for districting optimization models."""
    
    def __init__(self, G, k, deviation_persons, roots, contiguity=None, 
                 objective=None, use_weighted_distances=False, 
                 ideal_population=None, verbose=True):
        self.G = G
        self.DG = nx.DiGraph(G)
        self.k = k
        self.deviation_persons = deviation_persons
        self.roots = roots if isinstance(roots, list) else [roots]
        self.contiguity = contiguity
        self.objective = objective
        self.use_weighted_distances = use_weighted_distances
        self.verbose = verbose
        
        # Calculate population bounds
        if ideal_population is None:
            ideal_population = sum(self.DG.nodes[i]["TOTPOP"] for i in self.DG.nodes) / k
        self.DG._L = math.ceil(ideal_population - deviation_persons)
        self.DG._U = math.floor(ideal_population + deviation_persons)
        
        # Initialize model
        self.model = gp.Model()
        self.model._numCallbacks = 0
        self.model._numLazyCuts = 0
        
        # Validate inputs
        self._validate()
    
    def _validate(self):
        """Validate all inputs."""
        if not all(root in self.DG.nodes for root in self.roots):
            raise ValueError("All roots must be valid nodes in the graph.")
        if self.contiguity not in self.VALID_CONTIGUITY:
            raise ValueError(f"Invalid contiguity: {self.contiguity}")
        if self.objective not in self.VALID_OBJECTIVES:
            raise ValueError(f"Invalid objective: {self.objective}")
    
    def _create_variables(self):
        """Create decision variables. Override in subclasses."""
        raise NotImplementedError
    
    def _add_population_constraints(self):
        """Add population balance constraints. Override in subclasses."""
        raise NotImplementedError
    
    def _add_assignment_constraints(self):
        """Add assignment constraints. Override in subclasses."""
        raise NotImplementedError
    
    def _setup_objective(self):
        """Setup objective function."""
        if self.objective in {"hop_moi", "weighted_moi", "euclidean_moi"}:
            self._setup_moi_objective()
        elif self.objective == "cut_edges":
            self.model.setObjective(gp.quicksum(self.model._y), GRB.MINIMIZE)
        elif self.objective == "shared_perim":
            self._setup_shared_perim_objective()
        elif self.objective == "inverse_polsby_popper":
            self._setup_polsby_popper_objective()
    
    def _setup_moi_objective(self):
        """Setup Moment of Inertia objectives."""
        raise NotImplementedError
    
    def _get_predecessors(self, root):
        """Get predecessors using BFS or Dijkstra."""
        if self.use_weighted_distances:
            pred, dist = nx.dijkstra_predecessor_and_distance(
                self.DG, source=root, weight='weight'
            )
        else:
            pred = nx.predecessor(self.DG, source=root)
            dist = nx.single_source_shortest_path_length(self.DG, source=root)
        return pred, dist
    
    def _add_contiguity_constraints(self):
        """Add contiguity constraints."""
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
    
    def _add_tree_contiguity(self):
        """Add tree-based contiguity constraints."""
        raise NotImplementedError
    
    def _add_dist_contiguity(self):
        """Add distance-based contiguity constraints."""
        raise NotImplementedError
    
    def _add_dag_contiguity(self):
        """Add DAG-based contiguity constraints."""
        raise NotImplementedError
    
    def _add_shirabe_contiguity(self):
        """Add Shirabe flow-based contiguity constraints."""
        raise NotImplementedError
    
    def _add_cut_contiguity(self):
        """Add cut-based contiguity with callbacks."""
        self.model.Params.LazyConstraints = 1
        self.model._DG = self.DG
        self.model._contiguity = self.contiguity
    
    def build(self):
        """Build the complete model."""
        self._create_variables()
        self._add_assignment_constraints()
        self._add_population_constraints()
        self._setup_objective()
        self._add_contiguity_constraints()
        return self
    
    def solve(self, time_limit=3600, pool_search=0, pool_size=1, 
              cutoff=None, log_file=None, model_file=None):
        """Solve the model."""
        os.makedirs("logs", exist_ok=True)
        os.makedirs("models", exist_ok=True)
        
        # Set parameters
        self.model.Params.MIPGap = 0.00
        self.model.Params.FeasibilityTol = 1e-7
        self.model.Params.IntFeasTol = 1e-7
        self.model.Params.PoolSearchMode = pool_search
        self.model.Params.PoolSolutions = pool_size
        self.model.Params.TimeLimit = time_limit
        self.model.Params.OutputFlag = 1
        self.model.Params.LogToConsole = 1
        
        if cutoff is not None:
            self.model.Params.Cutoff = cutoff
        if log_file is not None:
            self.model.Params.LogFile = log_file
        if model_file is not None:
            self.model.write(model_file)
        
        self.model.update()
        
        # Optimize
        if hasattr(self.model, '_callback') and self.model._callback:
            self.model.optimize(self.model._callback)
        else:
            self.model.optimize()
        
        return self._build_metrics()
    
    def _build_metrics(self):
        """Build metrics dictionary from solved model."""
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
            "obj_bound": self.model.ObjBound,
            "obj_gap": self.model.MIPGap if self.model.SolCount > 0 else None,
            "nonzeros": self.model.NumNZs,
            "num_solutions": self.model.SolCount,
            "status": status_map.get(self.model.Status, f"Unknown ({self.model.Status})"),
            "contiguity": self.contiguity,
            "sparsity": (1 - (self.model.NumNZs / (self.model.NumConstrs * self.model.NumVars))) * 100,
            "num_callbacks": self.model._numCallbacks,
            "num_lazy_cuts": self.model._numLazyCuts,
        }


class SingleDistrictModel(DistrictingModel):
    """Model for finding a single optimal district."""
    
    def __init__(self, G, k, deviation_persons, root=None, **kwargs):
        # Auto-select root if not provided
        if root is None:
            maxp = max(G.nodes[i]["TOTPOP"] for i in G.nodes)
            root = [i for i in G.nodes if G.nodes[i]["TOTPOP"] == maxp][0]
        
        super().__init__(G, k, deviation_persons, roots=[root], **kwargs)
        self.root = self.roots[0]
    
    def _create_variables(self):
        """Create x[i] binary variables."""
        self.model._x = self.model.addVars(self.DG.nodes, name="x", vtype=GRB.BINARY)
        self.model._x[self.root].LB = 1  # Root must be selected
        
        # Create y variables for objectives that need them
        if self.objective not in {None, "hop_moi", "weighted_moi", "euclidean_moi"}:
            self.model._y = self.model.addVars(self.DG.edges, name="y", vtype=GRB.BINARY)
    
    def _add_assignment_constraints(self):
        """No assignment constraints for single district."""
        pass
    
    def _add_population_constraints(self):
        """Add L <= population <= U constraints."""
        if self.deviation_persons is not None:
            self.model.addConstr(
                gp.quicksum(self.DG.nodes[i]["TOTPOP"] * self.model._x[i] 
                           for i in self.DG.nodes) >= self.DG._L
            )
            self.model.addConstr(
                gp.quicksum(self.DG.nodes[i]["TOTPOP"] * self.model._x[i] 
                           for i in self.DG.nodes) <= self.DG._U
            )
    
    def _setup_moi_objective(self):
        """Setup MOI objectives for single district."""
        if self.objective == "hop_moi":
            dist = nx.single_source_shortest_path_length(self.DG, source=self.root)
        elif self.objective == "weighted_moi":
            dist = nx.single_source_dijkstra_path_length(self.DG, source=self.root, weight='weight')
        elif self.objective == "euclidean_moi":
            self.model.setObjective(
                gp.quicksum(sq_eucl_dist(self.G, i, self.root) * self.G.nodes[i]["TOTPOP"] * self.model._x[i] 
                           for i in self.G.nodes),
                GRB.MINIMIZE
            )
            return
        
        self.model.setObjective(
            gp.quicksum(dist[i]**2 * self.G.nodes[i]["TOTPOP"] * self.model._x[i] 
                       for i in self.G.nodes),
            GRB.MINIMIZE
        )
    
    def _add_tree_contiguity(self):
        """Tree contiguity for single district."""
        pred, _ = self._get_predecessors(self.root)
        self.model.addConstrs(
            self.model._x[i] <= self.model._x[pred[i][0]] 
            for i in pred if i != self.root
        )
    
    def _build_metrics(self):
        """Add district solution to metrics."""
        metrics = super()._build_metrics()
        if self.model.SolCount > 0:
            metrics["district"] = [i for i in self.G.nodes if self.model._x[i].x > 0.5]
        else:
            metrics["district"] = None
        return metrics


class MultiDistrictModel(DistrictingModel):
    """Model for finding k optimal districts."""
    
    VALID_OBJECTIVES = DistrictingModel.VALID_OBJECTIVES | {"bottleneck_polsby_popper"}
    
    def __init__(self, G, k, deviation_persons, roots, **kwargs):
        if len(roots) != k:
            raise ValueError(f"Number of roots must equal k={k}")
        super().__init__(G, k, deviation_persons, roots, **kwargs)
    
    def _create_variables(self):
        """Create x[i,j] binary variables."""
        self.model._x = {}
        for node in self.DG.nodes():
            for j in range(self.k):
                self.model._x[node, j] = self.model.addVar(
                    vtype=GRB.BINARY, name=f"x_{node}_{j}"
                )
        
        # Fix roots
        for j in range(self.k):
            self.model._x[self.roots[j], j].LB = 1
        
        # Create y variables for objectives that need them
        if self.objective in {"shared_perim", "perim", "inverse_polsby_popper", 
                              "cut_edges", "bottleneck_polsby_popper"}:
            self.model._y = self.model.addVars(self.DG.edges, self.k, name="y", vtype=GRB.BINARY)
        
        self.model.update()
    
    def _add_assignment_constraints(self):
        """Each node assigned to exactly one district."""
        self.model.addConstrs(
            gp.quicksum(self.model._x[i, j] for j in range(self.k)) == 1 
            for i in self.DG.nodes
        )
    
    def _add_population_constraints(self):
        """Add L <= population <= U for each district."""
        for j in range(self.k):
            self.model.addConstr(
                gp.quicksum(self.DG.nodes[i]["TOTPOP"] * self.model._x[i, j] 
                           for i in self.DG.nodes) >= self.DG._L
            )
            self.model.addConstr(
                gp.quicksum(self.DG.nodes[i]["TOTPOP"] * self.model._x[i, j] 
                           for i in self.DG.nodes) <= self.DG._U
            )
    
    def _setup_moi_objective(self):
        """Setup MOI objectives for multi-district."""
        for j in range(self.k):
            root = self.roots[j]
            
            if self.objective == "hop_moi":
                dist = nx.single_source_shortest_path_length(self.DG, source=root)
            elif self.objective == "weighted_moi":
                dist = nx.single_source_dijkstra_path_length(self.DG, source=root, weight='weight')
            elif self.objective == "euclidean_moi":
                for i in self.DG.nodes:
                    self.model._x[i, j].obj = sq_eucl_dist(self.G, i, root) * self.G.nodes[i]["TOTPOP"]
                continue
            
            for i in self.DG.nodes:
                self.model._x[i, j].obj = dist[i]**2 * self.G.nodes[i]["TOTPOP"]
    
    def _add_tree_contiguity(self):
        """Tree contiguity for multi-district."""
        for j in range(self.k):
            root = self.roots[j]
            pred, _ = self._get_predecessors(root)
            self.model.addConstrs(
                self.model._x[i, j] <= self.model._x[pred[i][0], j] 
                for i in self.DG.nodes if i != root
            )
    
    def _build_metrics(self):
        """Add districts solution to metrics."""
        metrics = super()._build_metrics()
        metrics["roots"] = self.roots
        if self.model.SolCount > 0:
            metrics["districts"] = [
                [i for i in self.G.nodes if self.model._x[i, j].x > 0.5] 
                for j in range(self.k)
            ]
        else:
            metrics["districts"] = None
        return metrics


# Updated function signatures
def single_district_mip(G, k, deviation_persons, root=None, **kwargs):
    """Build and solve single district model."""
    model = SingleDistrictModel(G, k, deviation_persons, root, **kwargs)
    model.build()
    metrics, gurobi_model = model.solve(
        time_limit=kwargs.get('time_limit', 3600),
        pool_search=kwargs.get('pool_search', 0),
        pool_size=kwargs.get('pool_size', 1),
        cutoff=kwargs.get('cutoff'),
        log_file=kwargs.get('log_file'),
        model_file=kwargs.get('model_file')
    ), model.model
    return metrics, gurobi_model


def multi_district_mip(G, k, deviation_persons, roots, **kwargs):
    """Build and solve multi-district model."""
    model = MultiDistrictModel(G, k, deviation_persons, roots, **kwargs)
    model.build()
    metrics, gurobi_model = model.solve(
        time_limit=kwargs.get('time_limit', 3600),
        pool_search=kwargs.get('pool_search', 0),
        pool_size=kwargs.get('pool_size', 1),
        cutoff=kwargs.get('cutoff'),
        log_file=kwargs.get('log_file'),
        model_file=kwargs.get('model_file')
    ), model.model
    return metrics, gurobi_model