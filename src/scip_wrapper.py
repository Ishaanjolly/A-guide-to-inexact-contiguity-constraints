from pyscipopt import Model as SCIPModel
import numpy as np
from typing import Optional, Union, List, Dict, Any

# Constants to mimic Gurobi's GRB constants
class GRB:
    # Variable types
    CONTINUOUS = 'C'
    BINARY = 'B'
    INTEGER = 'I'
    
    # Objective senses
    MINIMIZE = 'minimize'
    MAXIMIZE = 'maximize'
    
    # Status codes
    OPTIMAL = 'optimal'
    INF_OR_UNBD = 'infeasible or unbounded'
    INFEASIBLE = 'infeasible'
    UNBOUNDED = 'unbounded'
    INTERRUPTED = 'interrupted'
    ITERATION_LIMIT = 'iteration limit'
    NODE_LIMIT = 'node limit'
    TIME_LIMIT = 'time limit'
    SOLUTION_LIMIT = 'solution limit'
    LOADED = 'loaded'
    
    # Constraint senses
    LESS_EQUAL = '<'
    GREATER_EQUAL = '>'
    EQUAL = '='

class Var:
    """Wrapper for SCIP variable that mimics Gurobi's Var interface"""
    def __init__(self, scip_var, model, name=None):
        self._var = scip_var
        self._model = model  # Reference to the SCIP model
        self.VarName = name
        self.VType = None  # Will be set by addVar
        self.Obj = 0.0
        self.LB = -float('inf')
        self.UB = float('inf')
        
    def getAttr(self, attr):
        if attr == 'X':
            return self._model.getVal(self._var)
        elif attr == 'LB':
            return self.LB
        elif attr == 'UB':
            return self.UB
        elif attr == 'Obj':
            return self.Obj
        elif attr == 'VType':
            return self.VType
        else:
            raise ValueError(f"Attribute {attr} not supported in wrapper")
    
    @property
    def X(self):
        return self._model.getVal(self._var)
    
    def __add__(self, other):
        return LinExpr([(1, self)], 0) + other
    
    def __radd__(self, other):
        return LinExpr([(1, self)], 0) + other
    
    def __sub__(self, other):
        return LinExpr([(1, self)], 0) - other
    
    def __rsub__(self, other):
        return LinExpr([(1, self)], 0).__rsub__(other)
    
    def __mul__(self, other):
        return LinExpr([(other, self)], 0)
    
    def __rmul__(self, other):
        return LinExpr([(other, self)], 0)
    
    def __le__(self, other):
        return Constr(self, GRB.LESS_EQUAL, other)
    
    def __ge__(self, other):
        return Constr(self, GRB.GREATER_EQUAL, other)
    
    def __eq__(self, other):
        return Constr(self, GRB.EQUAL, other)

class LinExpr:
    """Linear expression wrapper"""
    def __init__(self, terms=None, constant=0):
        self.terms = terms if terms else []
        self.constant = constant
    
    def __add__(self, other):
        if isinstance(other, Var):
            return LinExpr(self.terms + [(1, other)], self.constant)
        elif isinstance(other, LinExpr):
            return LinExpr(self.terms + other.terms, self.constant + other.constant)
        elif isinstance(other, (int, float)):
            return LinExpr(self.terms, self.constant + other)
        else:
            return NotImplemented
    
    def __radd__(self, other):
        return self.__add__(other)
    
    def __sub__(self, other):
        if isinstance(other, Var):
            return LinExpr(self.terms + [(-1, other)], self.constant)
        elif isinstance(other, LinExpr):
            return LinExpr(self.terms + [(-coeff, var) for coeff, var in other.terms], 
                          self.constant - other.constant)
        elif isinstance(other, (int, float)):
            return LinExpr(self.terms, self.constant - other)
        else:
            return NotImplemented
    
    def __rsub__(self, other):
        if isinstance(other, (int, float)):
            return LinExpr([(-coeff, var) for coeff, var in self.terms], 
                          other - self.constant)
        else:
            return NotImplemented
    
    def __mul__(self, other):
        if isinstance(other, (int, float)):
            return LinExpr([(coeff * other, var) for coeff, var in self.terms], 
                          self.constant * other)
        else:
            return NotImplemented
    
    def __rmul__(self, other):
        return self.__mul__(other)
    
    def __le__(self, other):
        return Constr(self, GRB.LESS_EQUAL, other)
    
    def __ge__(self, other):
        return Constr(self, GRB.GREATER_EQUAL, other)
    
    def __eq__(self, other):
        return Constr(self, GRB.EQUAL, other)
    
    def getValue(self):
        """Calculate expression value with current solution"""
        return sum(coeff * var.X for coeff, var in self.terms) + self.constant

class Constr:
    """Constraint wrapper"""
    def __init__(self, lhs, sense, rhs):
        self.lhs = lhs
        self.sense = sense
        self.rhs = rhs
        self.ConstrName = None

class Model:
    """Main wrapper class that mimics Gurobi's Model interface"""
    
    def __init__(self, name=""):
        self._scip = SCIPModel(name)
        self._vars = []
        self._constrs = []
        self._status = None
        self.ModelName = name
        self._var_dict = {}  # For named variables
        
        # Set default parameters
        self.setParam('display/verblevel', 0)
    
    def _to_scip_expr(self, expr):
        """Convert Var/LinExpr/constant to SCIP expression"""
        if isinstance(expr, Var):
            return expr._var
        elif isinstance(expr, LinExpr):
            result = expr.constant
            for coeff, var in expr.terms:
                result = result + coeff * var._var
            return result
        elif isinstance(expr, (int, float)):
            return expr
        else:
            raise ValueError(f"Cannot convert {type(expr)} to SCIP expression")
        
    def addVar(self, lb=0.0, ub=float('inf'), obj=0.0, vtype=GRB.CONTINUOUS, name=None):
        """Add a variable to the model"""
        if vtype == GRB.BINARY:
            scip_var = self._scip.addVar(name=name, vtype='B', lb=lb, ub=ub, obj=obj)
        elif vtype == GRB.INTEGER:
            scip_var = self._scip.addVar(name=name, vtype='I', lb=lb, ub=ub, obj=obj)
        else:  # CONTINUOUS
            scip_var = self._scip.addVar(name=name, vtype='C', lb=lb, ub=ub, obj=obj)
        
        var = Var(scip_var, self._scip, name)  # Pass model reference
        var.LB = lb
        var.UB = ub
        var.Obj = obj
        var.VType = vtype
        
        self._vars.append(var)
        if name:
            self._var_dict[name] = var
        
        return var
    
    def addVars(self, *indices, lb=0.0, ub=float('inf'), obj=0.0, 
                vtype=GRB.CONTINUOUS, name=""):
        """Add multiple variables"""
        vars_dict = {}
        
        if len(indices) == 1:
            # Single dimension
            for i in indices[0]:
                var_name = f"{name}[{i}]" if name else None
                vars_dict[i] = self.addVar(lb, ub, obj, vtype, var_name)
        elif len(indices) == 2:
            # Two dimensions
            for i in indices[0]:
                for j in indices[1]:
                    var_name = f"{name}[{i},{j}]" if name else None
                    vars_dict[(i, j)] = self.addVar(lb, ub, obj, vtype, var_name)
        elif len(indices) == 3:
            # Three dimensions
            for i in indices[0]:
                for j in indices[1]:
                    for k in indices[2]:
                        var_name = f"{name}[{i},{j},{k}]" if name else None
                        vars_dict[(i, j, k)] = self.addVar(lb, ub, obj, vtype, var_name)
        
        return vars_dict
    
    def addConstr(self, constr, name=None):
        """Add a constraint to the model"""
        # Parse constraint
        lhs, sense, rhs = self._parse_constraint(constr)
        
        # Convert both sides to SCIP expressions
        scip_lhs = self._to_scip_expr(lhs)
        scip_rhs = self._to_scip_expr(rhs)
        
        # Create SCIP constraint with proper sense
        if sense == GRB.LESS_EQUAL:
            scip_constr = self._scip.addCons(scip_lhs <= scip_rhs, name=name)
        elif sense == GRB.GREATER_EQUAL:
            scip_constr = self._scip.addCons(scip_lhs >= scip_rhs, name=name)
        else:  # EQUAL
            scip_constr = self._scip.addCons(scip_lhs == scip_rhs, name=name)
        
        constr_obj = Constr(lhs, sense, rhs)
        constr_obj.ConstrName = name
        self._constrs.append(constr_obj)
        
        return scip_constr
    
    def _parse_constraint(self, constr):
        """Parse constraint from various formats"""
        if isinstance(constr, Constr):
            return constr.lhs, constr.sense, constr.rhs
        elif hasattr(constr, 'sense'):  # Handle comparison expressions
            return constr.lhs, constr.sense, constr.rhs
        else:
            raise ValueError("Invalid constraint format")
    
    def setObjective(self, expr, sense=GRB.MINIMIZE):
        """Set the objective function"""
        if isinstance(expr, (int, float)):
            # Constant objective
            self._scip.setObjective(expr, sense=sense)
        elif isinstance(expr, Var):
            # Single variable objective
            self._scip.setObjective(expr._var, sense=sense)
        elif isinstance(expr, LinExpr):
            # Linear expression - use helper method
            obj_expr = self._to_scip_expr(expr)
            self._scip.setObjective(obj_expr, sense=sense)
        else:
            # Try direct assignment
            self._scip.setObjective(expr, sense=sense)
    
    def optimize(self):
        """Solve the model"""
        self._scip.optimize()
        status = self._scip.getStatus()
        
        # Map SCIP status to Gurobi-like status
        if status == 'optimal':
            self._status = GRB.OPTIMAL
        elif status == 'infeasible':
            self._status = GRB.INFEASIBLE
        elif status == 'unbounded':
            self._status = GRB.UNBOUNDED
        elif status == 'timelimit':
            self._status = GRB.TIME_LIMIT
        else:
            self._status = status
        
        return self._status
    
    def getVars(self):
        """Get all variables"""
        return self._vars
    
    def getConstrs(self):
        """Get all constraints"""
        return self._constrs
    
    def getObjective(self):
        """Get the objective value"""
        return self._scip.getObjVal()
    
    @property
    def ObjVal(self):
        """Objective value property"""
        try:
            return self._scip.getObjVal()
        except:
            return None
    
    @property
    def Status(self):
        """Status property"""
        return self._status
    
    @property
    def NumVars(self):
        """Number of variables"""
        return len(self._vars)
    
    @property
    def NumConstrs(self):
        """Number of constraints"""
        return len(self._constrs)
    
    def setParam(self, param, value):
        """Set a parameter"""
        # Map common Gurobi parameters to SCIP parameters
        param_map = {
            'TimeLimit': 'limits/time',
            'MIPGap': 'limits/gap',
            'OutputFlag': 'display/verblevel',
            'Threads': 'parallel/maxnthreads',
            'NodeLimit': 'limits/nodes',
            'IterationLimit': 'lp/iterlim',
        }
        
        if param in param_map:
            self._scip.setParam(param_map[param], value)
        else:
            # Try direct parameter setting
            self._scip.setParam(param, value)
    
    def write(self, filename):
        """Write model to file"""
        self._scip.writeProblem(filename)
    
    def update(self):
        """Update model - not always needed in SCIP"""
        pass
    
    def reset(self):
        """Reset the model"""
        self._scip.freeTransform()
    
    def printStats(self):
        """Print model statistics"""
        print(f"Model: {self.ModelName}")
        print(f"Number of variables: {self.NumVars}")
        print(f"Number of constraints: {self.NumConstrs}")
        if self.Status:
            print(f"Status: {self.Status}")
            if self.ObjVal is not None:
                print(f"Objective value: {self.ObjVal:.6f}")

# Helper functions to mimic Gurobi's global functions
def quicksum(terms):
    """Quick sum of terms"""
    if isinstance(terms, dict):
        terms = list(terms.values())
    
    if not terms:
        return LinExpr([], 0)
    
    if isinstance(terms[0], Var):
        return LinExpr([(1, var) for var in terms], 0)
    elif isinstance(terms[0], LinExpr):
        result = LinExpr([], 0)
        for expr in terms:
            result.terms.extend(expr.terms)
            result.constant += expr.constant
        return result
    elif isinstance(terms[0], tuple):
        # Handle (coeff, var) pairs
        return LinExpr(terms, 0)
    else:
        return sum(terms)

# Example usage function
def demo():
    """Demonstrate the wrapper with a simple example"""
    # Original Gurobi code would look like:
    # from gurobipy import Model, GRB, quicksum
    
    # Using our wrapper instead:
    m = Model("demo")
    
    # Add variables
    x = m.addVar(vtype=GRB.BINARY, name="x")
    y = m.addVar(vtype=GRB.BINARY, name="y")
    z = m.addVar(vtype=GRB.CONTINUOUS, lb=0, ub=10, name="z")
    
    # Add constraint
    m.addConstr(x + y + z <= 5, "c1")
    m.addConstr(2*x + y >= 1, "c2")
    
    # Set objective
    m.setObjective(3*x + 2*y + z, GRB.MAXIMIZE)
    
    # Set parameters
    m.setParam('TimeLimit', 60)
    m.setParam('MIPGap', 0.01)
    
    # Solve
    m.optimize()
    
    # Print results
    print(f"Status: {m.Status}")
    print(f"Objective: {m.ObjVal}")
    
    for var in m.getVars():
        print(f"{var.VarName} = {var.X}")
    
    return m

if __name__ == "__main__":
    demo()