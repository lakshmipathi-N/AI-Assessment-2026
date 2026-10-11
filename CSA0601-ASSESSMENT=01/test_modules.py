"""Run: python tests/test_modules.py"""
import math, os, random, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from modules import *


def test_m1_count_and_agreement():
    rnd = random.Random(1)
    for n in (2, 3, 10, 57, 300):
        prods = [(f"t{rnd.randrange(max(1, n // 2))}", f"s{rnd.randrange(3)}") for _ in range(n)]
        marked, comps = m1_bruteforce(prods)
        assert comps == n * (n - 1) // 2 == m1_closed(n)
        assert marked == m1_hash(prods)


def test_m1_edge():
    assert m1_bruteforce([])[1] == 0 and m1_bruteforce([("a", "b")])[1] == 0
    marked, c = m1_bruteforce([("a", "s")] * 3)
    assert marked == {1, 2} and c == 3 and m1_hash([("a", "s")] * 3) == {1, 2}


def test_m2_exact():
    for n in range(1, 3000):
        ops, iters = m2_audit(n)
        assert ops == m2_closed(n), n
        if n >= 2:
            assert n - 1 <= ops <= 2 * n - 2, n          # Theta(n) sandwich
            assert iters == math.ceil(math.log2(n))
    assert m2_audit(1024) == (1023, 10)
    assert m2_audit(1025) == (2047, 11)


def test_s1():
    n = 400
    arr = list(range(n))
    assert sum(s1_sequential(arr, k)[1] for k in arr) == n * (n + 1) // 2
    assert s1_sequential(arr, -5) == (-1, n)


def test_s2():
    for n in (1, 2, 3, 7, 8, 100, 1000, 4097):
        arr = list(range(0, 2 * n, 2))
        worst = 0
        for q in range(-1, 2 * n + 1):
            a, ca = s2_binary_iterative(arr, q)
            b, cb = s2_binary_recursive(arr, q)
            assert a == b and ca == cb
            assert (a != -1) == (q % 2 == 0 and 0 <= q < 2 * n)
            worst = max(worst, ca)
        assert worst == s2_worst(n), n


def test_m4_m5_closed_forms():
    for k in range(0, 10):
        n = 2 ** k
        assert m4_current(n) == m4_current_closed(n)
        assert m4_redesign(n) == round(m4_redesign_closed(n))
    for k in range(0, 15):
        n = 2 ** k
        assert abs(m5_recurrence(n) - m5_closed(n)) < 1e-6 * max(1, m5_closed(n))


def test_report_bounds():
    for n in range(1, 5000):
        f = report_cost(n)
        assert 3 * n * n <= f <= 63 * n * n                 # c1=3, c2=63, n0=1
    for n in range(64, 5000):
        assert report_cost(n) <= 4 * n * n                   # c2=4, n0=64


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn(); print("PASS", name)
    print("ALL TESTS PASSED")
