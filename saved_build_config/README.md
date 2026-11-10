# Saved build configuration

Rebuild elsewhere:
1. Clone lb-stack-setup (`utils`) at the commit in `commits.txt`, and the projects at theirs.
2. Copy `config.json` to `utils/config.json`.
3. `make Moore`

Notes
- `useDistcc: false` is deliberate. With distcc on, the CMake compiler test failed with
  exit code 255 and no message. `utils/compile.sh` disables distcc only in
  `CMakeFiles/CMakeTmp`, while CMake 3.30 configures in `CMakeFiles/CMakeScratch/...`.
  Turning distcc off made Detector build. This diagnosis is untested for the root cause.
- `promptedModelSlot: lhcb-run5` answers the slot prompt.
- Checkouts: Detector, LHCb, Moore, Allen are on the nightly `lhcb-run5/458` merge commits
  (FETCH_HEAD of Moore: tag 'lhcb-run5/458' of lhcb-nightlies/Moore). Gaudi is on v40r6;
  Lbcom and Rec were not verified to be on the 458 tag. `commits.txt` has the exact commits.
  To reproduce: `git fetch ssh://git@gitlab.cern.ch:7999/lhcb-nightlies/<P>.git lhcb-run5/458 && git checkout FETCH_HEAD`
  (see `scifi_run5_work/checkout_nightly_run5_458.sh`).
- distcc install workaround, if you re-enable distcc: `ln -sfn ../lib contrib/linux-64/lib`
  (the installer puts include_server in `contrib/lib`, the pump looks in `contrib/linux-64/lib`).
- LCG 108c, binary tag x86_64_v3-el9-gcc15-opt.

## Known failure (checked on the nightly API, 2026-11-10)
`make Moore` fails in Lbcom: `Event/MCPicoCalDigit.h: No such file or directory`
(`Lbcom/Calo/CaloAssociators/src/PicoCalDigitLinker.cpp`). The nightly itself reports
Lbcom retcode=1 in lhcb-run5/458 (gcc15-opt), and also in 453-465. Rec has retcode=1 in
every build 440-457; LHCb fails from 459 on. No recent lhcb-run5 build had all of
Gaudi/Detector/LHCb/Lbcom/Rec/Allen/Moore at retcode 0. Source: https://lhcb-nightlies.web.cern.ch/api/v1/nightly/lhcb-run5/<N>/
