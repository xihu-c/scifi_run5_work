# Build report: `make Moore` on nightly lhcb-run5/458 (2026-11-10)

## Result
`make Moore` stops in Lbcom. The nightly build itself fails the same way.

```
Lbcom/Calo/CaloAssociators/src/PicoCalDigitLinker.cpp:15:10: fatal error: Event/MCPicoCalDigit.h: No such file or directory
```

## What built
Gaudi, Detector and LHCb built and installed. Lbcom failed. Rec, Allen and Moore were not reached.

## Findings
- Gaudi, Detector, LHCb, Lbcom, Rec, Moore and Allen were all fetched at `lhcb-run5/458`.
  Each project's `FETCH_HEAD` hash matches its current HEAD (see `commits.txt`).
- `MCPicoCalDigit` is not defined in LHCb, Detector, Rec or Lbcom. The only mention is Lbcom's own `PicoCalDigitLinker.cpp`.
- The commit "PicoCal Digit linker" is in Lbcom's history from 2026-10-14. LHCb's nightly commit is dated 2026-07-21.
- The nightly API reports Lbcom `retcode 1, errors 2` in 458 (`x86_64_v3-el9-gcc15-opt`):
  https://lhcb-nightlies.web.cern.ch/api/v1/nightly/lhcb-run5/458/

## Other nightly builds checked (gcc15-opt, retcode per project)
| Builds | Result |
|---|---|
| 440-457 | Rec fails in every build |
| 453-465 | Lbcom fails |
| 459 onwards | LHCb fails |
| 446-452 | Lbcom passes, Rec still fails |

No recent `lhcb-run5` build had Gaudi, Detector, LHCb, Lbcom, Rec, Allen and Moore all at retcode 0,
so another build number would not fix this.

## Earlier problems and what was changed
1. **Silent failure at `fast/Detector/install`.** The distcc installer puts `include_server` in
   `contrib/lib/python3.12/site-packages`, but `make.sh` looks in `contrib/linux-64/lib/...`.
   Workaround if distcc is re-enabled: `ln -sfn ../lib contrib/linux-64/lib`.
2. **CMake compiler test failed with exit code 255 and no message.** `utils/compile.sh` disables distcc only in
   `CMakeFiles/CMakeTmp`, while CMake 3.30 runs the test in `CMakeFiles/CMakeScratch/...`.
   Fix used: `useDistcc` set to `false` in `utils/config.json`. With it off, Detector built and installed.
   The cause is not confirmed beyond this.
3. The `Unset cache size limit` message you first saw is normal output from `ccache -M 0` in `utils/make.sh`.

## Options
- Update Lbcom or LHCb to commits that agree with each other. Rec may fail the same way, which was not checked.
- Build only what Moore needs. This needs CMake edits, and it was not checked whether Moore needs Lbcom's Calo associators.

## Files
- `scifi_run5_work/saved_build_config/config.json`: configuration used (`useDistcc: false`, slot `lhcb-run5`, LCG 108c, tag `x86_64_v3-el9-gcc15-opt`).
- `scifi_run5_work/saved_build_config/commits.txt`: commit of each project and of `utils`.
- `scifi_run5_work/checkout_nightly_run5_458.sh`: the checkout script (it ends with `make purge` and `make Moore`).
