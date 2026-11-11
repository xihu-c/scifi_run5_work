"""Measure TrackMasterFitter losses for standalone Run 5 SciFi seeds."""

from Configurables import LHCb__Det__LbDD4hep__DD4hepSvc as DD4hepSvc
from Moore import options, run_reconstruction
from Moore.config import Reconstruction
from RecoConf.upgrade2_track_fitting import fit_tracks
from RecoConf.upgrade2_reconstruction import get_pr_ft_tracks, tracking_efficiency
from PyConf.Algorithms import LHCb__Converters__fromV1TrackFutureTrack as fromV1TrackFutureTrack
from RecoConf.mc_checking import make_links_tracks_mcparticles


def seq_ft_seeding():
    seeds = get_pr_ft_tracks()
    fitted = fit_tracks(
        seeds["v1"], {"FT": seeds["Clusters"]}, name_postfix="SciFiSeeds"
    )
    fitted_info = dict(seeds)
    fitted_info["Tracks"] = fromV1TrackFutureTrack(
        InputTracksName=fitted
    ).OutputTracksName
    fitted_info["TrackLinks"] = make_links_tracks_mcparticles(
        InputTracks=fitted, LinksToLHCbIDs=seeds["ClusterLinks"]
    )
    return Reconstruction("ft_seed_kalman", [tracking_efficiency("FT", fitted_info)])


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
options.histo_file = "run5_ft_kalman_histos.root"
options.ntuple_file = "run5_ft_kalman_tuple.root"

DD4hepSvc().DetectorList = ["/world", "FT", "Magnet"]
run_reconstruction(options, seq_ft_seeding)
