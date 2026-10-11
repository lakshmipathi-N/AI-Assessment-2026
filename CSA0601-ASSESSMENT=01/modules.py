"""
ShopSphere scalability audit - implementations that COUNT their basic operations,
plus the closed forms derived analytically in the README.

M1  Duplicate-listing detector   : brute force O(n^2)   (+ hash-based redesign O(n))
M2  API rate limiter             : doubling-window audit, exact count 2^ceil(log2 n) - 1
M3  Product search               : S1 sequential, S2 binary (iterative + recursive)
M4  Recommendation engine        : T(n)=4T(n/2)+n  and redesign T(n)=2T(n/2)+n
M5  Sales analytics engine       : T(n)=2T(n/2)+n log n
Report generator                 : f(n)=3n^2+10 n log n+50
"""
import math


# ------------------------------------------------------------------ M1
def m1_bruteforce(products):
    """products: list of (title, seller). Basic op = title comparison in the inner loop.
    Returns (set of indices passed to MarkDuplicate, number of comparisons)."""
    n = len(products)
    comps, marked = 0, set()
    for i in range(n - 1):
        ti, si = products[i]
        for j in range(i + 1, n):
            comps += 1                          # Product[i].title = Product[j].title
            tj, sj = products[j]
            if ti == tj and si == sj:
                marked.add(j)
    return marked, comps


def m1_hash(products):
    """Redesign: one pass, remember (title, seller) pairs in a hash set. Expected Theta(n)."""
    seen, marked = set(), set()
    for j, p in enumerate(products):
        if p in seen:
            marked.add(j)
        else:
            seen.add(p)
    return marked


def m1_closed(n):
    return n * (n - 1) // 2


# ------------------------------------------------------------------ M2
def m2_audit(n):
    """Literal translation of the pseudocode. Returns (Audit operations, outer iterations)."""
    ops, iters, i = 0, 0, 1
    while i < n:
        for _ in range(i):                      # j = 0 .. i-1  -> i Audit() calls
            ops += 1
        i *= 2
        iters += 1
    return ops, iters


def m2_closed(n):
    k = (n - 1).bit_length() if n >= 1 else 0   # k = ceil(log2 n)
    return 2 ** k - 1


# ------------------------------------------------------------------ M3
def s1_sequential(arr, key):
    comps = 0
    for i in range(len(arr)):
        comps += 1
        if arr[i] == key:
            return i, comps
    return -1, comps


def s2_binary_iterative(arr, key):
    lo, hi, comps = 0, len(arr) - 1, 0
    while lo <= hi:
        mid = (lo + hi) // 2
        comps += 1                              # one comparison per halving
        if arr[mid] == key:
            return mid, comps
        if key < arr[mid]:
            hi = mid - 1
        else:
            lo = mid + 1
    return -1, comps


def s2_binary_recursive(arr, key, lo=0, hi=None):
    if hi is None:
        hi = len(arr) - 1
    if lo > hi:
        return -1, 0
    mid = (lo + hi) // 2
    if arr[mid] == key:
        return mid, 1
    if key < arr[mid]:
        idx, c = s2_binary_recursive(arr, key, lo, mid - 1)
    else:
        idx, c = s2_binary_recursive(arr, key, mid + 1, hi)
    return idx, c + 1


def s2_worst(n):
    return int(math.floor(math.log2(n))) + 1


def s1_average(n, p):
    """p*(n+1)/2 + (1-p)*n"""
    return p * (n + 1) / 2 + (1 - p) * n


# ------------------------------------------------------------------ M4 (recurrences executed literally)
def m4_current(n):                              # T(n)=4T(n/2)+n, T(1)=1
    if n <= 1:
        return 1
    return sum(m4_current(n // 2) for _ in range(4)) + n


def m4_redesign(n):                             # T(n)=2T(n/2)+n, T(1)=1
    if n <= 1:
        return 1
    return sum(m4_redesign(n // 2) for _ in range(2)) + n


def m4_current_closed(n):  return 2 * n * n - n
def m4_redesign_closed(n): return n * math.log2(n) + n


# ------------------------------------------------------------------ M5 + report
def m5_recurrence(n):                           # T(n)=2T(n/2)+n log2 n, T(1)=1
    if n <= 1:
        return 1
    return 2 * m5_recurrence(n // 2) + n * math.log2(n)


def m5_closed(n):
    L = math.log2(n)
    return n * L * (L + 1) / 2 + n


def report_cost(n):
    return 3 * n * n + 10 * n * math.log2(n) + 50
