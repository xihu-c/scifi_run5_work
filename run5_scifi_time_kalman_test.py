"""FT-only jialu timing seeding + optional 7D Kalman fit.

Run from an output directory:
  ../../Moore/run gaudirun.py ../run5_scifi_time_kalman_test.py
Optional ./scifi_time_config.json keys: input_file, events, sigma_ns,
readout_model, fibre_speed, time_seeding, time_kalman, fit, geometry, tag.
The MC readout model applies Gaussian smearing ONCE to MCHit truth time.
"""

import json
from pathlib import Path

from Configurables import LHCb__Det__LbDD4hep__DD4hepSvc as DD4hepSvc
from Moore.config import Reconstruction
from PyConf.Algorithms import (
    LHCb__Converters__fromV1TrackFutureTrack as ToFuture,
)
from PyConf.Algorithms import (
    SciFiTimeKalman,
)
from RecoConf.hlt2_tracking import (
    make_PrHybridSeeding_pr_tracks,
    make_PrStoreSciFiTimeHits_hits,
)
from RecoConf.legacy_rec_hlt1_tracking import make_FTRawBankDecoder_clusters
from RecoConf.mc_checking import make_links_tracks_mcparticles
from RecoConf.upgrade2_reconstruction import get_pr_ft_tracks, tracking_efficiency
from RecoConf.upgrade2_track_fitting import fit_scifi_tracks_with_time

from Moore import options, run_reconstruction

config_path = Path("scifi_time_config.json")
cfg = json.loads(config_path.read_text()) if config_path.exists() else {}
sigma = float(cfg.get("sigma_ns", 0.8))
readout = bool(cfg.get("readout_model", True))
fibre_speed = float(cfg.get("fibre_speed", 150.0))
tag = cfg.get("tag", "scifi_time_7d")


def sequence():
    hits = make_PrStoreSciFiTimeHits_hits(
        sigma_ns=sigma, apply_readout_model=readout, fibre_speed=fibre_speed
    )
    timing_options = {
        "SciFiTimeSigmaNs": sigma,
        "SciFiTimePairDeltaT": True,
        "SciFiTimeT2PredictWindow": True,
        "SciFiTimeTripletFitVeto": True,
        "SciFiTimeFullXZFitVeto": True,
        "SciFiTimeFullTrackFitVeto": True,
    }
    with make_PrHybridSeeding_pr_tracks.bind(
        use_time=bool(cfg.get("time_seeding", True)),
        time_selection_options=timing_options
        if cfg.get("time_seeding", True)
        else None,
    ):
        seeds = get_pr_ft_tracks(make_ft_hits=lambda: hits)
    tracks = seeds["v1"]
    if cfg.get("fit", True):
        with SciFiTimeKalman.bind(OutputLevel=int(cfg.get("fit_output_level", 3))):
            tracks = fit_scifi_tracks_with_time(
                tracks,
                make_FTRawBankDecoder_clusters(),
                hits,
                sigma_ns=sigma,
                fibre_speed=fibre_speed if readout else 0.0,
                use_time=bool(cfg.get("time_kalman", True)),
            )
    checked = dict(seeds)
    checked["Tracks"] = ToFuture(InputTracksName=tracks).OutputTracksName
    # Fitter rejection leaves gaps in v1 keys; associate the dense final container.
    checked["TrackLinks"] = make_links_tracks_mcparticles(
        InputTracks=checked["Tracks"], LinksToLHCbIDs=seeds["ClusterLinks"]
    )
    return Reconstruction("scifi_time_kalman", [tracking_efficiency("FT", checked)])


options.input_files = [
    cfg.get(
        "input_file",
        "/eos/lhcb/wg/rta/WP6/UII/Jan2026/MINBIAS/1p3E34/"
        "MINBIAS_proto-v00.03_L1p3E34_Slot_9-30000000-100ev-20260129-Extended.digi",
    )
]
options.input_type = "ROOT"
options.simulation = True
options.geometry_version = cfg.get("geometry", "run5/proto-v00.03-picocalfix")
options.conditions_version = "sim11/run5-ideal"
options.evt_max = int(cfg.get("events", 20))
options.print_freq = 5
options.scheduler_legacy_mode = False
options.histo_file = f"{tag}_histos.root"
options.ntuple_file = f"{tag}_tuple.root"
DD4hepSvc().DetectorList = ["/world", "FT", "Magnet"]
run_reconstruction(options, sequence)
