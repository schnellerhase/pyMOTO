"""
Example of the design of cantilever for minimum volume subjected to stress constraints.

References:

Implemented by @artofscience (s.koppen@tudelft.nl), based on:

Verbart, A., Langelaar, M., & Keulen, F. V. (2017).
A unified aggregation and relaxation approach for stress-constrained topology optimization.
Structural and Multidisciplinary Optimization, 55, 663-679.
DOI: https://doi.org/10.1007/s00158-016-1524-0
"""

import numpy as np

import pymoto as pym
from pymoto.modules.assembly import get_B, get_D

# Problem settings
nx, ny = 50, 100  # Domain size
xmin, filter_radius, volfrac = 1e-9, 2, 1.0

scaling_objective = 100.0
maximum_vm_stress = 0.4

displacement_constraint = False
scaling_displacement_constraint = 10.0
max_displacement = 20.0


class ConstraintAggregation(pym.Module):
    """
    Unified aggregation and relaxation.

    Implemented by @artofscience (s.koppen@tudelft.nl), based on:

    Verbart, A., Langelaar, M., & Keulen, F. V. (2017).
    A unified aggregation and relaxation approach for stress-constrained topology optimization.
    Structural and Multidisciplinary Optimization, 55, 663-679.
    DOI: https://doi.org/10.1007/s00158-016-1524-0
    """

    def _prepare(self, P=10):
        self.P = P

    def _response(self, x):
        """
        a = x + 1
        b = aggregation(a)
        c = b - 1
        """
        self.n = len(x)
        self.x = x
        self.y = self.x + 1
        self.z = self.y ** self.P
        z = (np.sum(self.z) / self.n) ** (1 / self.P)  # P-mean aggregation function
        return z - 1

    def _sensitivity(self, dfdc):
        return (dfdc / self.n) * (np.sum(self.z) / self.n) ** (1 / self.P - 1) * self.y ** (self.P - 1)


if __name__ == "__main__":
    # Set up the domain
    domain = pym.DomainDefinition(nx, ny)

    # Node and dof groups
    nodes_left = domain.get_nodenumber(0, np.arange(ny + 1))
    dofs_left = np.repeat(nodes_left * 2, 2, axis=-1) + np.tile(np.arange(2), ny + 1)

    # Setup rhs for loadcase
    f = np.zeros(domain.nnodes * 2)  # Generate a force vector
    f[2 * domain.get_nodenumber(nx, ny // 2) + 1] = 1.0

    # Initial design
    s_variables = pym.Signal('x', state=volfrac * np.ones(domain.nel))

    # Setup optimization problem
    fn = pym.Network()

    # Filtering
    s_filtered_variables = fn.append(pym.DensityFilter(s_variables, domain=domain, radius=filter_radius))

    # SIMP penalization
    s_penalized_variables = fn.append(pym.MathGeneral(s_filtered_variables, expression=f"{xmin} + {1 - xmin}*(inp0^3)"))

    # Assemble stiffness matrix
    s_K = fn.append(pym.AssembleStiffness(s_penalized_variables, domain=domain, bc=dofs_left))

    # Solve
    s_force = pym.Signal('f', state=f)
    s_displacement = fn.append(pym.LinSolve([s_K, s_force]))

    # Calculate stress components
    s_stress = fn.append(pym.Stress(s_displacement, domain=domain))

    # Calculate Von-Mises stress
    V = np.array([[1, -0.5, 0], [-0.5, 1, 0], [0, 0, 3]])  # Vandermonde matrix
    s_stress_vm2 = fn.append(pym.EinSum([s_stress, pym.Signal(state=V), s_stress], expression='ij,ik,kj->j'))
    s_stress_vm = fn.append(pym.MathGeneral(s_stress_vm2, expression='sqrt(inp0)'))

    # Stress constraint
    s_stress_constraints = fn.append(pym.Scaling(s_stress_vm, maxval=maximum_vm_stress, scaling=1.0))
    s_stress_constraints_scaled = fn.append(pym.EinSum([s_filtered_variables, s_stress_constraints],
                                                       expression='i,i->i'))
    s_stress_constraint = fn.append(ConstraintAggregation([s_stress_constraints_scaled], P=10))
    s_stress_constraint.tag = "Stress constraint"

    # Volume
    s_volume = fn.append(pym.EinSum(s_filtered_variables, expression='i->'))

    # Objective
    s_objective = fn.append(pym.Scaling([s_volume], scaling=scaling_objective))
    s_objective.tag = "Objective (volume)"

    # Plotting
    s_stress_scaled = fn.append(pym.EinSum([s_filtered_variables, s_stress_vm], expression='i,i->i'))
    module_plotstress = pym.PlotDomain(s_stress_scaled, domain=domain, cmap='jet')

    module_plotdomain = pym.PlotDomain(s_filtered_variables, domain=domain, saveto="out/design")
    responses = [s_objective, s_stress_constraint]

    if displacement_constraint:
        # Output displacement (is a complex value)
        s_compliance = fn.append(pym.EinSum([s_displacement, s_force], expression='i,i->'))

        # Displacement constraint
        s_compliance_constraint = fn.append(
            pym.Scaling(s_compliance, scaling=scaling_displacement_constraint, maxval=max_displacement))
        s_compliance_constraint.tag = "Displacement constraint"

        responses.append(s_compliance_constraint)

    module_plotiter = pym.PlotIter(responses)
    fn.append(module_plotdomain, module_plotstress, module_plotiter)

    # Optimization
    pym.minimize_mma(fn, [s_variables], responses, verbosity=2, maxit=300)
