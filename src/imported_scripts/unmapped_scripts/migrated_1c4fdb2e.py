def solve() -> None:
    s = input()
    n = len(s)
    ans = 0
    for i in range(n):
        for j in range(i, n):
            sub = s[i : j + 1]
            if len(set(sub)) == len(sub):
                ans += 1


solve()
