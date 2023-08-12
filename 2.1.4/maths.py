from scipy.optimize import fsolve
import numpy as np

def solve_for_r(x1, y1, x2, y2, theta):
    # Equations to be solved
    def equations(vars):
        r, theta0 = vars
        eq1 = (x2 - x1) - r * (np.cos(theta + theta0) - np.cos(theta0))
        eq2 = (y2 - y1) - r * (np.np.sin(theta + theta0) - np.sin(theta0))
        return [eq1, eq2]

    # Initial guess for r and theta0
    initial_guess = [1, 0]

    # Solve for r and theta0
    solution = fsolve(equations, initial_guess)

    r_solution, theta0_solution = solution
    return r_solution, theta0_solution
