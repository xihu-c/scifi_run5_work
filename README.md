# SciFi / Run 5 (lhcb-run5/458) work

Paths are relative to the stack root (`..` from this directory).

| Item | Purpose |
|---|---|
| `PARTNER_GUIDE.md` | Step-by-step: build the stack and run the seeding test |
| `SciFi_seeding_code.md` | Map of the SciFi seeding code (Rec, Allen, event model, Moore config) |
| `checkout_nightly_run5_458.sh` | Fetch/checkout `lhcb-run5/458` in 7 projects (the final `make purge` / `make Moore` lines are commented out) |
| `saved_build_config/` | Build configuration (`config.json`, `commits.txt`), `README.md`, `BUILD_REPORT.md` |
| `run5_ft_seeding_test.py` | Run 5 SciFi seeding efficiency test (`PrHybridSeeding` + `FTTrackChecker`) on a Run 5 DIGI sample |
| `make_seeding_report.py` | Builds `run5_test/SEEDING_REPORT.md` and PNG plots from the log and histograms (`../../Moore/run python ../make_seeding_report.py` from `run5_test/`) |
| `run5_test/` | Output of that test: `log.txt` and the two ROOT files |
| `patches/Rec_PrMCTools_sensor_fix.patch` | Rec fix: `DeTV::sensor(...)` calls use `TVChannelID::SensorID` (branch `xihu/fix-prmctools-tv-sensor`) |
| `patches/Detector_picocal_geometry.diff` | Detector: new geometry `compact/run5/proto-v00.03-picocalfix` = `proto-v00.03` with PicoCal `proto-run5-v01.00` |

## Deviations from the nightly 458 tag
- Lbcom is at `ee3fbefa` (one commit before the tag): LHCb `run5` lacks `MCPicoCalDigit`.
- `utils/config.json`: `useDistcc: false`, `promptedModelSlot: lhcb-run5`.
- Rec has the sensor fix above. The Detector geometry copy must be recreated
  (`cp -r Detector/compact/run5/proto-v00.03 Detector/compact/run5/proto-v00.03-picocalfix`, then set
  `version:PicoCal` to `proto-run5-v01.00` in its `versions.xml`; see the diff).

## Run the seeding test
```bash
mkdir -p scifi_run5_work/run5_test && cd scifi_run5_work/run5_test
../../Moore/run gaudirun.py ../run5_ft_seeding_test.py
```
Input: `upgrade2_minbias_1p0e34_Jan2026` (DIGI with MC truth, on CVMFS), 20 events.
Result (20 events, FT-reconstructible long tracks): efficiency 89.5%, >5 GeV 97.0%, purity 99.4%,
ghosts 13.6%, clones 0%.
