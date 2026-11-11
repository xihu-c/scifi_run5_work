"""External smearing of MC hit times (NOT part of the stack).

Usage: python smear_times.py mc_times.txt out.txt --sigma-ps 100 [--seed 1] [--vf-ns-per-m 5.5]

Input  lines: event channelID t_mc[ns] y_mc[mm] n_mchits   (from extract_mc_times.py)
Output lines: event channelID t_hit[ns]                     (what Rec reads)

t_hit = t_mc + tau + Gaussian(0, sigma)
tau   = |Y_ro - y| / v_f  with Y_ro = +-2500 mm (SiPM at the outer end of the
        half, approximate) and is only added if --vf-ns-per-m is given.
"""
import argparse

import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("infile")
ap.add_argument("outfile")
ap.add_argument("--sigma-ps", type=float, required=True)
ap.add_argument("--seed", type=int, default=1)
ap.add_argument("--vf-ns-per-m", type=float, default=None)
a = ap.parse_args()

d = np.loadtxt(a.infile)
ev, ch, t, y = d[:, 0].astype(np.int64), d[:, 1].astype(np.int64), d[:, 2], d[:, 3]
rng = np.random.default_rng(a.seed)
if a.vf_ns_per_m is not None:
    t = t + np.abs(np.sign(y) * 2500.0 - y) * 1e-3 * a.vf_ns_per_m
t = t + rng.normal(0.0, a.sigma_ps * 1e-3, size=t.shape)
with open(a.outfile, "w") as f:
    for e, c, tt in zip(ev, ch, t):
        f.write(f"{e} {c} {tt:.5f}\n")
print("wrote", len(t), "hits, sigma =", a.sigma_ps, "ps")
