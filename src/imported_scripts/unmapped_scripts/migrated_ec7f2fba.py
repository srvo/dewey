import math


def solve_quadratic_equation(a, b, c):
    delta = b**2 - 4 * a * c
    if delta >= 0:
        x1 = (-b - math.sqrt(delta)) / (2 * a)
        x2 = (-b + math.sqrt(delta)) / (2 * a)
        return x1, x2
    return "No real roots"
