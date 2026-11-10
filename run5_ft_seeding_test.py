from Configurables import LHCb__Det__LbDD4hep__DD4hepSvc as DD4hepSvc
from Moore import options, run_reconstruction
from Moore.config import Reconstruction
from RecoConf.upgrade2_reconstruction import get_pr_ft_tracks, tracking_efficiency


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
options.evt_max = 20
options.print_freq = 5
options.scheduler_legacy_mode = False
options.histo_file = "run5_seeding_histos.root"
options.ntuple_file = "run5_seeding_tuple.root"

DD4hepSvc().DetectorList = ["/world", "FT", "Magnet"]
run_reconstruction(options, seq_ft_seeding)
