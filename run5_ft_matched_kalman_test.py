"""Measure fit failures for TV + SciFi matched long tracks (20 events)."""
from Configurables import LHCb__Det__LbDD4hep__DD4hepSvc as DD4hepSvc
from Moore import options, run_reconstruction
from Moore.config import Reconstruction
from RecoConf.upgrade2_reconstruction import (
    get_pr_ft_tracks, get_tv_tracks, make_PrMatchNN_tracks,
)
from RecoConf.upgrade2_track_fitting import fit_tracks, select_tracks
from PyConf.Algorithms import LHCb__Converters__fromV1TrackFutureTrack as Convert


def seq_ft_seeding():
    seeds = get_pr_ft_tracks()
    tv = get_tv_tracks()
    matched = make_PrMatchNN_tracks(tv, seeds)
    fitted = fit_tracks(
        matched["v1"], {"TV": tv["HitsAsMap"], "FT": seeds["Clusters"]},
        name_postfix="Match_FT_Fitted",
    )
    # Force both the fitter and the subsequent configured quality selection.
    selected = select_tracks("SciFiMatch", fitted, MaxChi2DoF=7.5)
    return Reconstruction("ft_matched_kalman", [Convert(InputTracksName=selected)])


options.input_files = [
    "/cvmfs/lhcbdev.cern.ch/testfiledb-mirror/rta/WP6/UII/Jan2026/MINBIAS/1p0E34/"
    "MINBIAS_proto-v00.03_L1p0E34_Slot_9-30000000-100ev-20260129-Extended.digi"
]
options.input_type = "ROOT"
options.simulation = True
options.geometry_version = "run5/proto-v00.03-picocalfix"
options.conditions_version = "sim11/run5-ideal"
options.evt_max = 20
options.print_freq = 5
options.scheduler_legacy_mode = False
options.histo_file = "run5_ft_matched_kalman_histos.root"
options.ntuple_file = "run5_ft_matched_kalman_tuple.root"

DD4hepSvc().DetectorList = ["/world", "TV", "FT", "Magnet"]
run_reconstruction(options, seq_ft_seeding)
