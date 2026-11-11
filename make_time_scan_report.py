"""Compare seeding results across time-selection configurations.

Run from run5_test/:  python3 ../make_time_scan_report.py TIME_SCAN_REPORT.md log_baseline... 
Usage: make_time_scan_report.py out.md label=log.txt [label=log.txt ...]
The first entry is the reference (normally the no-time baseline).
Table: long-track (FT) efficiency, ghost rate, and the fraction of seeds kept by the time selection.
"""
import re
import sys

out = sys.argv[1]
entries = [a.split("=", 1) for a in sys.argv[2:]]

eff_pat = re.compile(r"INFO\s+(02_long_FT|02_long)\s*:\s+(\d+) from\s+(\d+) \[\s*([\d.]+) %\]")
ghost_pat = re.compile(r"\*\*\*\* FT\s+(\d+) tracks including\s+(\d+) ghosts \[\s*([\d.]+) %\]")
kept_pat = re.compile(r"Seeds passing time selection\"\s*\|\s*(\d+)\s*\|\s*(\d+)")


def parse(path):
    r = {}
    for line in open(path, errors="replace"):
        m = eff_pat.search(line)
        if m:
            r[m.group(1)] = (int(m.group(2)), int(m.group(3)), float(m.group(4)))
        m = ghost_pat.search(line)
        if m:
            r["ghost"] = (int(m.group(1)), int(m.group(2)), float(m.group(3)))
        m = kept_pat.search(line)
        if m:
            r["kept"] = (int(m.group(1)), int(m.group(2)))
    return r


rows = [(label, parse(path)) for label, path in entries]
lines = [
    "# SciFi seeding with hit times: configuration comparison",
    "",
    "| Configuration | Long FT eff [%] | Ghost rate [%] | Seeds out | Time-selection pass [%] |",
    "|---|---|---|---|---|",
]
for label, r in rows:
    eff = r.get("02_long_FT", (0, 0, float("nan")))[2]
    g = r.get("ghost", (0, 0, float("nan")))
    kept = r.get("kept")
    kp = f"{100.0 * kept[1] / kept[0]:.1f}" if kept and kept[0] else "n/a"
    lines.append(f"| {label} | {eff:.2f} | {g[2]:.2f} | {g[0]} | {kp} |")
open(out, "w").write("\n".join(lines) + "\n")
print("\n".join(lines))
