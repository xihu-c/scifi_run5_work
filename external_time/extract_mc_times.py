"""External (outside the stack) extraction of MC truth hit times for SciFi lite clusters.

Run with:  Moore/run python extract_mc_times.py <digi file> <n_events> <out.txt>

Output: one line per cluster:  event_number  channelID  t_mc[ns]  y_mc[mm]  n_mchits
t_mc is the earliest linked MCHit::time() (flight time from the collision, no
fibre delay, no resolution).  y_mc is the y of that MC hit mid-point.
Nothing here is part of the stack: smearing is done afterwards by smear_times.py.
"""
import sys

import GaudiPython as GP
from Configurables import LHCb__Det__LbDD4hep__DD4hepSvc as DD4hepSvc
from Moore import options
from PyConf.Algorithms import PrintHeader
from PyConf.application import configure, configure_input, make_odin
from PyConf.control_flow import CompositeNode, NodeLogic
from RecoConf.data_from_file import boole_links_digits_mchits, mc_unpacker

infile, nevt, outfile = sys.argv[1], int(sys.argv[2]), sys.argv[3]

options.input_files = [infile]
options.input_type = "ROOT"
options.simulation = True
options.geometry_version = "run5/proto-v00.03-picocalfix"
options.conditions_version = "sim11/run5-ideal"
options.evt_max = nevt
options.gaudipython_mode = True
options.scheduler_legacy_mode = True
DD4hepSvc().DetectorList = ["/world", "FT", "Magnet"]

config = configure_input(options)
odin = make_odin()
loader = PrintHeader(
    ODINLocation=odin,
    ExtraInputs=[boole_links_digits_mchits("FTLiteClusters"), mc_unpacker("MCFTHits")],
)
node = CompositeNode("load", [loader], combine_logic=NodeLogic.NONLAZY_OR)
config.update(configure(options, node))

app = GP.AppMgr()
evt = app.evtsvc()
odin_loc = odin.location
n_lines = 0
with open(outfile, "w") as out:
    for i in range(nevt):
        app.run(1)
        links = evt["/Event/Link/Raw/FT/LiteClusters2MCHits"]
        hits = evt["/Event/MC/FT/Hits"]
        o = evt[odin_loc]
        if not links or not hits or not o:
            break
        evnum = o.getData().eventNumber()
        refs = links.linkReference()
        for kv in links.keyIndex():
            chan, ref_idx = kv.first, kv.second
            best_t, best_y, n = None, 0.0, 0
            while ref_idx >= 0:
                r = refs[ref_idx]
                h = hits.containedObject(r.objectKey())
                if h:
                    n += 1
                    if best_t is None or h.time() < best_t:
                        best_t, best_y = h.time(), h.midPoint().y()
                ref_idx = r.nextIndex()
            if best_t is not None:
                out.write(f"{evnum} {chan} {best_t:.5f} {best_y:.3f} {n}\n")
                n_lines += 1
print("WROTE", n_lines, "lines to", outfile)
