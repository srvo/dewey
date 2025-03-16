import math


def solve_quadratic_equation(a, b, c):
    delta = b**2 - 4 * a * c
    if delta >= 0:
        x1 = (-b - math.sqrt(delta)) / (2 * a)
        x2 = (-b + math.sqrt(delta)) / (2 * a)
        return x1, x2
    return None


def is_prime(n) -> bool:
    if n < 2:
        return False
    return all(n % i != 0 for i in range(2, int(n**0.5) + 1))
