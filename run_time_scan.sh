#!/bin/bash
# usage: run_time_scan.sh TAG TIME_FILE SIGMA_NS TIME_SELECTION [EVT_MAX] [MAX_T_CHI2] [T0_WINDOW]
# Run from scifi_run5_work/run5_test. Writes time_config.json, then runs the job.
python3 - "$@" <<'PY'
import json, sys
a = sys.argv[1:]
c = {"TAG": a[0], "TIME_FILE": a[1], "SIGMA_NS": a[2], "TIME_SELECTION": a[3]}
if len(a) > 4 and a[4]: c["EVT_MAX"] = a[4]
if len(a) > 5 and a[5]: c["MAX_T_CHI2"] = a[5]
if len(a) > 6 and a[6]: c["T0_WINDOW"] = a[6]
json.dump(c, open("time_config.json", "w"))
PY
../../Moore/run gaudirun.py ../run5_ft_seeding_time_test.py > log_$1.txt 2>&1
rm -f time_config.json
