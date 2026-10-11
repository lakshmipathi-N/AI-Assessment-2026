"""
Run: python src/experiment.py
Writes results/*.csv|json and plots/*.png

ASSUMPTION: server speed = 10^9 basic operations per second (the exponent is lost in the
question paper text). Change OPS_PER_SEC if your paper says otherwise.
"""
import csv, json, math, os, random, sys, time
sys.path.insert(0, os.path.dirname(__file__))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from modules import *

ROOT = os.path.join(os.path.dirname(__file__), "..")
RES, PLT = os.path.join(ROOT, "results"), os.path.join(ROOT, "plots")
OPS_PER_SEC = 1e9
WINDOW_S = 600                                   # 10 minutes
SENSITIVITY = (1e9, 1e8)


def write_csv(name, rows):
    with open(os.path.join(RES, name), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)


def fmt_time(s):
    if s < 1e-3: return f"{s*1e6:.2f} µs"
    if s < 1:    return f"{s*1e3:.2f} ms"
    if s < 120:  return f"{s:.2f} s"
    if s < 7200: return f"{s/60:.2f} min"
    return f"{s/3600:.2f} h"


def main():
    out = {}

    # ---------- 1. exactness checks: implementation vs closed form ----------
    ver = []
    for k in range(1, 10):
        n = 2 ** k
        ver.append(dict(n=n,
            M1_measured=m1_bruteforce([(str(i), "s") for i in range(n)])[1], M1_formula=m1_closed(n),
            M2_measured=m2_audit(n)[0], M2_formula=m2_closed(n),
            M4_current_measured=m4_current(n), M4_current_formula=m4_current_closed(n),
            M4_redesign_measured=m4_redesign(n), M4_redesign_formula=round(m4_redesign_closed(n)),
            M5_measured=round(m5_recurrence(n), 3), M5_formula=round(m5_closed(n), 3)))
    write_csv("verification.csv", ver)
    for r in ver:
        assert r["M1_measured"] == r["M1_formula"] and r["M2_measured"] == r["M2_formula"]
        assert r["M4_current_measured"] == r["M4_current_formula"]
        assert r["M4_redesign_measured"] == r["M4_redesign_formula"]
        assert abs(r["M5_measured"] - r["M5_formula"]) < 1e-2

    # M2 specifically (part b): n = 1024 and neighbours
    out["M2_checks"] = {str(n): dict(zip(("ops", "outer_iterations"), m2_audit(n)),
                                     n_log_n=round(n * math.log2(n)))
                        for n in (1000, 1024, 1025, 100_000, 1_000_000)}

    # ---------- 2. M1 timing: quadratic vs hash redesign ----------
    rnd = random.Random(7)
    m1_rows = []
    for n in (500, 1000, 2000, 4000, 8000):
        prods = [(f"title{rnd.randrange(int(n * 0.9))}", f"seller{rnd.randrange(20)}") for _ in range(n)]
        t0 = time.perf_counter(); marked, comps = m1_bruteforce(prods); tb = time.perf_counter() - t0
        t0 = time.perf_counter(); marked2 = m1_hash(prods);              th = time.perf_counter() - t0
        assert marked == marked2 and comps == n * (n - 1) // 2
        m1_rows.append(dict(n=n, comparisons=comps, brute_time_s=tb, hash_time_s=th, duplicates=len(marked)))
    m1_rows[0]["time_ratio_vs_previous"] = ""
    for a, b in zip(m1_rows, m1_rows[1:]):
        b["time_ratio_vs_previous"] = b["brute_time_s"] / a["brute_time_s"]
    write_csv("m1_timing.csv", m1_rows)
    slope = math.log(m1_rows[-1]["brute_time_s"] / m1_rows[0]["brute_time_s"]) / math.log(8000 / 500)
    out["M1_loglog_slope"] = slope

    # ---------- 3. search: exhaustive small n, sampled mid n, exhaustive 10^6 for S2 ----------
    n = 2000
    arr = list(range(n))
    hit_total = sum(s1_sequential(arr, k)[1] for k in arr)
    out["S1_exhaustive_n2000"] = dict(avg_hit=hit_total / n, theory_hit=(n + 1) / 2,
                                      miss=s1_sequential(arr, -1)[1],
                                      avg_p05=0.5 * hit_total / n + 0.5 * n,
                                      theory_p05=s1_average(n, 0.5))
    n = 100_000
    arr = list(range(n)); step = n // 400
    hits = [s1_sequential(arr, i * step)[1] for i in range(400)]       # evenly spread positions
    miss = s1_sequential(arr, -1)[1]
    out["S1_stratified_n100000"] = dict(avg_hit=sum(hits) / len(hits), theory_hit=(n + 1) / 2,
                                        miss=miss, avg_p05=0.5 * sum(hits) / len(hits) + 0.5 * miss,
                                        theory_p05=s1_average(n, 0.5))
    N = 1_000_000
    arr = list(range(0, 2 * N, 2))
    tot, best, worst = 0, 10**9, 0
    for k in range(N):
        _, c = s2_binary_iterative(arr, arr[k]); tot += c; best = min(best, c); worst = max(worst, c)
    miss_worst = max(s2_binary_iterative(arr, q)[1] for q in range(-1, 2 * N, 20001))
    out["S2_exhaustive_n1e6"] = dict(avg_hit=tot / N, theory_hit=math.log2(N + 1) - 1,
                                     best=best, worst_hit=worst, worst_miss_sample=miss_worst,
                                     worst_formula=s2_worst(N))
    rec_ok = all(s2_binary_recursive(arr, arr[k]) == s2_binary_iterative(arr, arr[k])
                 for k in range(0, N, 997))
    out["S2_recursive_equals_iterative"] = rec_ok
    out["S1_avg_formula_n1e6_p05"] = s1_average(1_000_000, 0.5)

    # ---------- 4. projections ----------
    modules = [
        ("M1 duplicate detector (brute force)", m1_closed),
        ("M2 API rate limiter", m2_closed),
        ("S1 sequential search (p=0.5 avg)", lambda n: s1_average(n, 0.5)),
        ("S1 sequential search (worst)", lambda n: n),
        ("S2 binary search (worst)", s2_worst),
        ("M4 current  T=4T(n/2)+n", m4_current_closed),
        ("M4 redesign T=2T(n/2)+n", m4_redesign_closed),
        ("M5 analytics T=2T(n/2)+n log n", m5_closed),
        ("Report generator f(n)", report_cost),
        ("M1 redesign (hash, ~n)", lambda n: n),
    ]
    proj = []
    for name, fn in modules:
        row = dict(module=name)
        for n in (100_000, 1_000_000):
            ops = fn(n)
            row[f"ops_n{n}"] = ops
            for rate in SENSITIVITY:
                row[f"time_s_n{n}_rate{rate:.0e}"] = ops / rate
        row["fits_10min_at_1e9_n1e6"] = row["time_s_n1000000_rate1e+09"] <= WINDOW_S
        row["fits_10min_at_1e8_n1e6"] = row["time_s_n1000000_rate1e+08"] <= WINDOW_S
        proj.append(row)
    write_csv("projection.csv", proj)

    # largest n that fits the window (bisection)
    def n_max(fn, budget):
        lo, hi = 2.0, 1e15
        if fn(hi) <= budget: return None
        for _ in range(200):
            mid = (lo + hi) / 2
            if fn(mid) <= budget: lo = mid
            else: hi = mid
        return lo
    headroom = {}
    for name, fn in modules:
        if "S1" in name or "S2" in name or "M2" in name: continue
        headroom[name] = {f"{r:.0e}": n_max(fn, r * WINDOW_S) for r in SENSITIVITY}
    out["max_n_in_10min_window"] = headroom

    # doubling behaviour
    dbl = []
    for n in (10**5, 10**6):
        dbl.append(dict(n=n,
            M4_current_ratio=m4_current_closed(2 * n) / m4_current_closed(n),
            M4_redesign_ratio=m4_redesign_closed(2 * n) / m4_redesign_closed(n),
            M5_ratio=m5_closed(2 * n) / m5_closed(n),
            M1_ratio=m1_closed(2 * n) / m1_closed(n)))
    write_csv("doubling.csv", dbl)

    json.dump(out, open(os.path.join(RES, "experiment_summary.json"), "w"), indent=2)

    # ---------- 5. plots ----------
    ns = [10 ** (e / 4) for e in range(4, 29)]
    fig, ax = plt.subplots(figsize=(8.5, 5.2))
    curves = [("M1 brute force  n(n-1)/2", m1_closed, "tab:red"),
              ("M4 current  2n²−n", m4_current_closed, "tab:orange"),
              ("Report  3n²+10n log n+50", report_cost, "tab:brown"),
              ("M5  n log n (log n+1)/2 + n", m5_closed, "tab:purple"),
              ("M4 redesign  n log n + n", m4_redesign_closed, "tab:green"),
              ("M2  2^⌈log n⌉ − 1", m2_closed, "tab:blue"),
              ("S2 binary  ⌊log n⌋+1", s2_worst, "tab:cyan")]
    for lab, fn, c in curves:
        ax.loglog(ns, [fn(int(x)) for x in ns], color=c, label=lab)
    ax.axhline(OPS_PER_SEC * WINDOW_S, color="k", ls="--", label="10-min budget (6×10¹¹ ops @10⁹/s)")
    for x in (1e5, 1e6): ax.axvline(x, color="grey", ls=":", lw=1)
    ax.set_xlabel("n (products)"); ax.set_ylabel("basic operations"); ax.grid(True, which="both", alpha=.3)
    ax.set_title("ShopSphere modules – growth of operation counts"); ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(os.path.join(PLT, "growth_curves.png"), dpi=140); plt.close(fig)

    xs = list(range(2, 4200))
    fig, ax = plt.subplots(figsize=(8, 4.8))
    ax.plot(xs, [m2_closed(x) for x in xs], label="M2 exact ops = 2^⌈log₂n⌉ − 1")
    ax.plot(xs, [x - 1 for x in xs], "--", label="lower bound n − 1")
    ax.plot(xs, [2 * x - 2 for x in xs], "--", label="upper bound 2n − 2")
    ax.plot(xs, [x * math.log2(x) for x in xs], ":", color="red", label="claimed n log₂ n")
    ax.set_xlabel("n"); ax.set_ylabel("Audit operations"); ax.grid(alpha=.3); ax.legend()
    ax.set_title("M2: exact count is sandwiched between n−1 and 2n−2 ⇒ Θ(n)")
    fig.tight_layout(); fig.savefig(os.path.join(PLT, "m2_sawtooth.png"), dpi=140); plt.close(fig)

    fig, ax = plt.subplots(figsize=(6.4, 4.4))
    ax.loglog([r["n"] for r in m1_rows], [r["brute_time_s"] for r in m1_rows], "o-", color="tab:red", label="M1 brute force")
    ax.loglog([r["n"] for r in m1_rows], [r["hash_time_s"] for r in m1_rows], "o-", color="tab:green", label="M1 hash redesign")
    ax.set_xlabel("n"); ax.set_ylabel("seconds"); ax.grid(True, which="both", alpha=.3); ax.legend()
    ax.set_title(f"M1 measured time (log-log slope ≈ {slope:.2f})")
    fig.tight_layout(); fig.savefig(os.path.join(PLT, "m1_timing.png"), dpi=140); plt.close(fig)

    show = [r for r in proj if r["module"] not in ("S1 sequential search (p=0.5 avg)", "S1 sequential search (worst)", "M1 redesign (hash, ~n)")]
    fig, ax = plt.subplots(figsize=(9, 4.8))
    labels = [r["module"].split("  ")[0][:34] for r in show]
    vals = [max(r["time_s_n1000000_rate1e+09"], 1e-9) for r in show]
    cols = ["tab:red" if v > WINDOW_S else "tab:green" for v in vals]
    ax.barh(labels, vals, color=cols); ax.set_xscale("log"); ax.invert_yaxis()
    ax.axvline(WINDOW_S, color="k", ls="--"); ax.text(WINDOW_S, -0.6, " 10 min", va="bottom")
    ax.set_xlabel("seconds at n = 1,000,000 (10⁹ ops/s)")
    ax.set_title("Projected running time at n = 10⁶")
    fig.tight_layout(); fig.savefig(os.path.join(PLT, "projection_1M.png"), dpi=140); plt.close(fig)

    # ---------- console summary ----------
    print("M2 checks:", json.dumps(out["M2_checks"]))
    print("M1 slope:", round(slope, 3))
    for k in ("S1_exhaustive_n2000", "S1_stratified_n100000", "S2_exhaustive_n1e6"):
        print(k, json.dumps(out[k]))
    print("S2 recursive == iterative:", rec_ok)
    for r in proj:
        print(f'{r["module"]:<40} ops@1e6={r["ops_n1000000"]:.4g}  t@1e9={fmt_time(r["time_s_n1000000_rate1e+09"])}  t@1e8={fmt_time(r["time_s_n1000000_rate1e+08"])}')
    print("headroom:", json.dumps(headroom, default=lambda x: round(x)))
    print("doubling:", dbl)


if __name__ == "__main__":
    main()
