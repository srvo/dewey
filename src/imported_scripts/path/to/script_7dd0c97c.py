import math


def solve_quadratic_equation(a, b, c):
    d = b**2 - 4 * a * c
    if d < 0:
        return "No real roots"
    if d == 0:
        x = -b / (2 * a)
        return "One real root: " + str(x)
    x1 = (-b - math.sqrt(d)) / (2 * a)
    x2 = (-b + math.sqrt(d)) / (2 * a)
    return "Two real roots: " + str(x1) + " and " + str(x2)
