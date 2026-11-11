"""Run 5 SciFi seeding test with hit times.

Moore/run drops environment variables, so settings come from ./time_config.json
(written by run_time_scan.sh), with the same keys as below.
  TIME_FILE      sidecar table (event channelID time[ns]); empty = no time
  SIGMA_NS       per-hit time resolution used in the fit [ns]
  TIME_SELECTION 1 to apply the time selection in the seeding
  MAX_T_CHI2     chi2/ndf cut (default off)
  T0_WINDOW      half window on a_t - zRef*k/c [ns] (default off)
  SLOPE_PRIOR    sigma of the b_t prior around k/c [ns/mm] (default: free)
  TAG            suffix for output files
  EVT_MAX        number of events (default 20)
"""
import json
import os

from Configurables import LHCb__Det__LbDD4hep__DD4hepSvc as DD4hepSvc
from Moore import options, run_reconstruction
from Moore.config import Reconstruction
from RecoConf.hlt2_tracking import make_PrHybridSeeding_pr_tracks
from RecoConf.upgrade2_reconstruction import get_pr_ft_tracks, tracking_efficiency

_cfg = json.load(open("time_config.json")) if os.path.exists("time_config.json") else {}


def env(key, default=None):
    return str(_cfg[key]) if key in _cfg else default


tag = env("TAG", "baseline")

seed_opts = {}
if env("TIME_SELECTION", "0") == "1":
    seed_opts["TimeSelection"] = True
seed_opts["SigmaT"] = float(env("SIGMA_NS", "0.1"))
if env("MAX_T_CHI2"):
    seed_opts["MaxTimeChi2PerDoF"] = float(env("MAX_T_CHI2"))
if env("T0_WINDOW"):
    seed_opts["T0Window"] = float(env("T0_WINDOW"))
if env("SLOPE_PRIOR"):
    seed_opts["TimeSlopePriorSigma"] = float(env("SLOPE_PRIOR"))


def seq_ft_seeding():
    ft_tracks = get_pr_ft_tracks()
    return Reconstruction("ft_seeding", [tracking_efficiency("FT", ft_tracks)])


options.input_files = [
    "/cvmfs/lhcbdev.cern.ch/testfiledb-mirror/rta/WP6/UII/Jan2026/MINBIAS/1p0E34/"
    "MINBIAS_proto-v00.03_L1p0E34_Slot_9-30000000-100ev-20260129-Extended.digi"
]
options.input_type = "ROOT"
options.simulation = True
options.geometry_version = "run5/proto-v00.03-picocalfix"
options.conditions_version = "sim11/run5-ideal"
options.evt_max = int(env("EVT_MAX", "20"))
options.print_freq = 5
options.scheduler_legacy_mode = False
options.histo_file = f"seeding_histos_{tag}.root"
options.ntuple_file = f"seeding_tuple_{tag}.root"

DD4hepSvc().DetectorList = ["/world", "FT", "Magnet"]
# global_bind: the reconstruction is built lazily inside run_reconstruction
make_PrHybridSeeding_pr_tracks.global_bind(
    hit_time_file=env("TIME_FILE", ""), time_selection_options=seed_opts
)
run_reconstruction(options, seq_ft_seeding)
