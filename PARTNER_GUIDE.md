# Partner guide: build the Run 5 stack and test SciFi seeding

Goal: build Moore against nightly `lhcb-run5/458` and run the Run 5 SciFi seeding test.
Everything here was done on lxplus9 (el9, 16 cores, AFS). Expect roughly 1-3 hours for a full build without distcc.

## 1. Set up the stack
```bash
cd /afs/cern.ch/work/<you>/stack          # any AFS/work dir with lots of space
curl -sSL https://gitlab.cern.ch/lhcb-core/dev-tools/lb-stack-setup/raw/master/setup.py | python3 - stack
cd stack
```
You need a CERN kerberos ticket and a GitLab ssh key (`ssh -T git@gitlab.cern.ch -p 7999` should work).
Copy this `scifi_run5_work/` directory into the stack root.

## 2. Configure
When `make` asks for the model slot, answer `lhcb-run5`. Then disable distcc
(its pump fails silently on this setup, and the CMake compiler test fails with it on):
```bash
utils/config.py useDistcc false
```
`scifi_run5_work/saved_build_config/config.json` is the config used here (LCG 108c, `x86_64_v3-el9-gcc15-opt`).

## 3. Check out the nightly 458 sources
```bash
bash scifi_run5_work/checkout_nightly_run5_458.sh
```
It checks out `lhcb-run5/458` in Gaudi, Detector, LHCb, Lbcom, Rec, Moore, Allen (detached HEAD).
(Its last two lines `make purge` / `make Moore` are comments: run them yourself.)
Expected HEADs are in `saved_build_config/commits.txt`.

## 4. Apply the two fixes (nightly 458 itself does not build)
1. **Lbcom**: `PicoCalDigitLinker.cpp` needs `Event/MCPicoCalDigit.h`, which LHCb `run5` lacks.
   ```bash
   git -C Lbcom checkout ee3fbefa     # one commit before the tag
   ```
2. **Rec**: `PrMCTools` calls `DeTV::sensor(int)`, removed from Detector.
   ```bash
   git -C Rec apply ../scifi_run5_work/patches/Rec_PrMCTools_sensor_fix.patch
   ```
   (Optionally create a branch first: `git -C Rec switch -c <name>`.)

## 5. Build
```bash
make purge                       # optional, clean start
make Moore > build.log 2>&1      # builds Gaudi, Detector, LHCb, Lbcom, Rec, Allen, Moore
```
Success = no `FAILED:` lines and `Moore/InstallArea/x86_64_v3-el9-gcc15-opt/` populated.
A `Unset cache size limit` message is the normal ccache message, not an error.
If a project fails, `make fast/<Project>/install` rebuilds just that one;
`make fast/Rec/install BUILDFLAGS="-k 0"` keeps going past errors to list them all.

## 6. Geometry fix for the test
The Detector PicoCal builder needs a constant missing from the PicoCal version used by `run5/proto-v00.03`.
Create a copy with a newer PicoCal (SciFi is unaffected):
```bash
cd Detector/compact/run5
cp -r proto-v00.03 proto-v00.03-picocalfix
sed -i 's/name="version:PicoCal" value="proto-run5-v00.00"/name="version:PicoCal" value="proto-run5-v01.00"/' proto-v00.03-picocalfix/versions.xml
cd -
```
(`patches/Detector_picocal_geometry.diff` shows the exact change.)

## 7. Run the seeding test
```bash
mkdir -p scifi_run5_work/run5_test && cd scifi_run5_work/run5_test
../../Moore/run gaudirun.py ../run5_ft_seeding_test.py > log.txt 2>&1
grep "FTTrackChecker" log.txt | grep -v Histo
```
It runs `PrHybridSeeding` on 20 events of the Run 5 sample `upgrade2_minbias_1p0e34_Jan2026`
(DIGI with MC truth, read from CVMFS, no download needed) and prints efficiencies, ghost rate, purity.
Compare with our result (rows ending `_FT` are the FT-reconstructible ones):

| Quantity | Our result |
|---|---|
| Ghost rate | 13.6 % (event average 11.1 %) |
| Long tracks, efficiency | 89.5 % (2388/2668), purity 99.4 % |
| Long tracks > 5 GeV | 97.0 % (1132/1167) |
| Clones | 0 % |

After the run, make a human-readable report (table + plots) from `run5_test/`:
```bash
../../Moore/run python ../make_seeding_report.py   # -> SEEDING_REPORT.md + 2 PNGs
```

Edit `options.evt_max`, `options.input_files` in `run5_ft_seeding_test.py` for more events or other samples
(other Run 5 DIGI samples: `upgrade2_minbias_1p5e34_Jan2026`, `..._1p3e34_Jan2026` in the TestFileDB).
Output: `run5_seeding_histos.root`, `run5_seeding_tuple.root`.

## 8. Known issues
- Moore's `standalone_hlt2_seeding` example (Run 3 style) does not work with Run 5 Moore; use `run5_ft_seeding_test.py`.
- Rec `Vis/PhoenixAlgs` is disabled in Run 5, so Phoenix event-display dumpers are unavailable.
- Nightly 458 itself fails in Lbcom and Rec on the dashboard (see `saved_build_config/BUILD_REPORT.md`).
- Seeding code map: `SciFi_seeding_code.md`.
