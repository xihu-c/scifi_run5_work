"""Turn the seeding test output into a readable report.

Run from run5_test/ (needs ROOT + matplotlib, e.g. via ../../Moore/run):
    ../../Moore/run python ../make_seeding_report.py [log.txt] [histos.root]
Writes SEEDING_REPORT.md and PNG plots next to the log.
"""

import re
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import ROOT

log_file = sys.argv[1] if len(sys.argv) > 1 else "log.txt"
histo_file = sys.argv[2] if len(sys.argv) > 2 else "run5_seeding_histos.root"
DIR = "Track/FTTrackChecker/FT/"

LABELS = {
    "02_long": "Long tracks (any T hits)",
    "03_long_P>5GeV": "Long tracks, p > 5 GeV",
    "04_long_fromB": "Long tracks from B decays",
    "06_UT+T_strange": "Strange-daughter tracks (UT+T)",
    "13_hasT_electrons": "All T-track electrons",
    "01_hasT": "All tracks with T hits",
}


def parse_log(path):
    ghost = None
    rows = {}
    pat = re.compile(
        r"INFO\s+(\S+)\s*:\s+(\d+) from\s+(\d+) \[\s*([\d.]+) %\]\s+(\d+) clones "
        r"\[\s*([\d.]+) %\], purity:\s*([\d.]+) %, hitEff:\s*([\d.]+) %"
    )
    for line in open(path):
        if "FTTrackChecker" not in line:
            continue
        m = re.search(
            r"\*\*\*\* FT\s+(\d+) tracks including\s+(\d+) ghosts \[([\d.]+) %\], "
            r"Event average ([\d.]+) %",
            line,
        )
        if m:
            ghost = tuple(float(x) for x in m.groups())
        m = pat.search(line)
        if m:
            rows[m.group(1)] = [float(x) for x in m.groups()[1:]]
    return ghost, rows


def eff_curve(f, name, ax, xlabel, rebin=1, xlim=None):
    num = f.Get(DIR + name + "_reconstructed")
    den = f.Get(DIR + name + "_reconstructible")
    if not num or not den:
        return
    if rebin > 1:
        num, den = num.Rebin(rebin, "n"), den.Rebin(rebin, "d")
    n = np.array([num.GetBinContent(i) for i in range(1, num.GetNbinsX() + 1)])
    d = np.array([den.GetBinContent(i) for i in range(1, den.GetNbinsX() + 1)])
    x = np.array([den.GetBinCenter(i) for i in range(1, den.GetNbinsX() + 1)])
    w = np.array([den.GetBinWidth(i) for i in range(1, den.GetNbinsX() + 1)])
    ok = d > 0
    eff = np.where(ok, n / np.where(ok, d, 1), np.nan)
    err = np.where(ok, np.sqrt(np.clip(eff * (1 - eff), 0, None) / np.where(ok, d, 1)), np.nan)
    ax2 = ax.twinx()
    ax2.bar(x, d, width=w, color="lightgrey", alpha=0.6, label="reconstructible")
    ax2.set_ylabel("reconstructible tracks", color="grey")
    ax.set_zorder(ax2.get_zorder() + 1)
    ax.patch.set_visible(False)
    ax.errorbar(x, eff * 100, yerr=err * 100, fmt="o", ms=4, color="C0")
    ax.set_ylim(0, 105)
    ax.set_xlabel(xlabel)
    if xlim:
        ax.set_xlim(*xlim)
    ax.set_ylabel("seeding efficiency [%]")
    ax.grid(alpha=0.3)


def main():
    ghost, rows = parse_log(log_file)
    f = ROOT.TFile(histo_file)

    fig, axs = plt.subplots(2, 2, figsize=(11, 8))
    fig.suptitle("PrHybridSeeding efficiency, long tracks with T hits (Run 5 minbias)")
    eff_curve(f, "02_long_FT_P", axs[0, 0], "p [MeV]", rebin=2, xlim=(0, 40000))
    eff_curve(f, "02_long_FT_Pt", axs[0, 1], "pT [MeV]", rebin=2, xlim=(0, 5000))
    eff_curve(f, "02_long_FT_Eta", axs[1, 0], "eta", xlim=(1.5, 5.5))
    eff_curve(f, "02_long_FT_z", axs[1, 1], "origin z [mm]", rebin=10, xlim=(-200, 250))
    fig.tight_layout()
    fig.savefig("seeding_efficiency_long.png", dpi=130)

    rows = {k[:-3]: v for k, v in rows.items() if k.endswith("_FT")}
    cats = [c for c in LABELS if c in rows]
    fig, ax = plt.subplots(figsize=(9, 4.5))
    y = np.arange(len(cats))
    ax.barh(y, [rows[c][2] for c in cats], color="C0")
    for i, c in enumerate(cats):
        ax.text(rows[c][2] + 1, i, f"{rows[c][2]:.1f}%  ({int(rows[c][0])}/{int(rows[c][1])})", va="center")
    ax.set_yticks(y)
    ax.set_yticklabels([LABELS[c] for c in cats])
    ax.invert_yaxis()
    ax.set_xlim(0, 120)
    ax.set_xlabel("efficiency [%] (T-station-only seeds, FT-reconstructible)")
    fig.tight_layout()
    fig.savefig("seeding_efficiency_summary.png", dpi=130)

    out = ["# SciFi seeding report (PrHybridSeeding, Run 5)", ""]
    if ghost:
        out += [
            f"**Reconstructed seeds:** {int(ghost[0])}, of which **{int(ghost[1])} ghosts "
            f"({ghost[2]:.1f} %)**, event average {ghost[3]:.1f} %.",
            "",
        ]
    out += [
        "| Category | Found / reconstructible | Efficiency | Clones | Purity | Hit eff. |",
        "|---|---|---|---|---|---|",
    ]
    for c in cats:
        n, d, e, cl, clp, pur, he = rows[c]
        out.append(
            f"| {LABELS[c]} | {int(n)} / {int(d)} | {e:.1f} % | {int(cl)} ({clp:.1f} %) | {pur:.1f} % | {he:.1f} % |"
        )
    out += [
        "",
        "Rows use the `_FT` variant of each category (tracks reconstructible in the SciFi alone).",
        "",
        "![summary](seeding_efficiency_summary.png)",
        "",
        "![long tracks](seeding_efficiency_long.png)",
        "",
    ]
    open("SEEDING_REPORT.md", "w").write("\n".join(out))
    print("wrote SEEDING_REPORT.md, seeding_efficiency_summary.png, seeding_efficiency_long.png")


main()
