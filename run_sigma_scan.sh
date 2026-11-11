#!/bin/bash
# Scan sigma_t with the chi2/ndf cut (and optional T0 window). Run from run5_test/.
# usage: run_sigma_scan.sh [MAX_T_CHI2] [T0_WINDOW] [SUFFIX]
CH=${1:-3}; W=${2:-}; SUF=${3:-chi}
for s in 50 100 200 500 1000; do
  ../run_time_scan.sh ${SUF}_s${s} $PWD/../external_time/times_sigma${s}ps.txt $(python3 -c "print($s/1000)") 1 20 $CH $W
done
