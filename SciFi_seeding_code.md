# SciFi seeding: code map

Paths are relative to the stack root. Line counts are in parentheses.
Found by file and symbol search; function-level behaviour was only skimmed.

## 1. Rec (CPU, HLT2): `PrHybridSeeding`

| File | Role |
|---|---|
| `Rec/Pr/PrAlgorithms/src/PrHybridSeeding.cpp` (1865) | The algorithm. `operator()` runs the cases and the two parts: `findXProjections` -> `removeClonesX*` -> `addStereo` -> `flagHits`, then `RecoverTrack`, `removeClones_*`, `makeLHCbTracks`. |
| `Rec/Pr/PrAlgorithms/src/PrHybridSeedTrack.h` (276) | Seed track and x-z track classes (`Hybrid::SeedTrack`, `SeedTrackX`). |
| `Rec/Pr/PrAlgorithms/src/HoughSearch.h` (358) | Hough-style search helper, included by `PrHybridSeeding.cpp`. |
| `Rec/Pr/PrAlgorithms/src/PrTrackFitterXZ.h` (115) | x-z parabola fit. |
| `Rec/Pr/PrAlgorithms/src/PrTrackFitterYZ.h` (136) | y-z line fit (stereo hits). |
| `Rec/Pr/PrAlgorithms/src/PrTrackFitterXYZ.h` (171) | Combined 3D fit. |
| `Rec/Pr/PrAlgorithms/CMakeLists.txt` | Registers `src/PrHybridSeeding.cpp` and `src/PrResidualSeeding.cpp`. |
| `Rec/Pr/PrAlgorithms/src/PrResidualSeeding.cpp` (89) | `PrResidualSeeding`: takes a track collection and the seeds, outputs seeds. Used as `PrResidualSeedingLong` in Moore. |
| `Rec/Pr/PrKernel/include/PrKernel/PrHit.h` | Hit type used by the search. |

Hits come from `PrStoreSciFiHits` (`Rec/Pr/PrAlgorithms/src/PrStoreSciFiHits.cpp`).

## 2. Event model

| File | Role |
|---|---|
| `LHCb/Event/TrackEvent/include/Event/PrSeedTracks.h` | Output SoA container (`Seeding::Tracks`). |
| `Rec/Pr/PrConverters/src/fromPrTracksV1Track.cpp` | `fromPrSeedingTracksV1Tracks`: Pr seeds -> v1 `LHCb::Track`. |

## 3. Allen (GPU/CPU, HLT1)

Device code, `Allen/device/SciFi/hybridseeding/`:

| File | Role |
|---|---|
| `src/seed_xz.cu` (479), `include/seed_xz.cuh` | Stage 1: x-z tracks from triplets (hit index packed in 32 bits, `maxNHits`, `MaxHitIdx`). |
| `src/seed_confirmTracks.cu` (374), `include/seed_confirmTracks.cuh` | Stage 2: adds stereo hits to the x-z tracks (inferred from the name and the config below). |
| `include/hybrid_seeding_case.cuh`, `include/hybrid_seeding_helpers.cuh` | Layer-case definitions and shared helpers. |
| `consolidate/src/SeedingCopyTrackXZHitNumber.cu` | Copies per-track hit numbers (x-z tracks). |
| `consolidate/src/SeedingCopyTrackHitNumber.cu` | Copies per-track hit numbers (seeds). |
| `consolidate/src/ConsolidateSciFiSeeding.cu` (251) | Writes the final seed tracks into contiguous memory. |

Shared event model:
- `Allen/device/event_model/SciFi/include/SciFiDefinitions.cuh`
- `Allen/device/event_model/SciFi/include/SciFiEventModel.cuh`

Configuration:
- `Allen/configuration/python/AllenConf/scifi_reconstruction.py`: `make_seeding_XZ_tracks` (`seed_xz_t`), `make_seeding_tracks` (`seed_confirmTracks_t`, `seeding_copy_track_hit_number_t`, `seed_confirmTracks_consolidate_t`).
- `Allen/configuration/python/AllenConf/hlt1_reconstruction.py` (around lines 102-103): calls both.

Validation:
- Sequences: `Allen/configuration/python/AllenSequences/seeding_validation.py`, `seeding_xz_validation.py`.
- Host validators: `Allen/host/validators/src/HostSeedingValidator.cpp`, `HostSeedingXZValidator.cpp`, `HostUnmatchedSeedingValidator.cpp`.
- Checker: `Allen/checker/tracking/src/PrepareTracks.cpp`.

## 4. Moore configuration (HLT2 / reco)

| File | Role |
|---|---|
| `Moore/Hlt/RecoConf/python/RecoConf/hlt2_tracking.py` | `make_PrHybridSeeding_tracks` (runs `PrHybridSeeding` + `fromPrSeedingTracksV1Tracks`), `make_seeding_tracks`. |
| `Moore/Hlt/RecoConf/python/RecoConf/run5_default_tracking.py` | Run-5 seeding setup (FT `PrHybridSeeding`, and an MP variant via `PrMPTracker`). |
| `Moore/Hlt/RecoConf/python/RecoConf/hlt2_cheated_tracking.py` | Cheated (MC-truth) pattern recognition for seeds. |
| `Moore/Hlt/RecoConf/python/RecoConf/mc_checking.py` | `PrTrackChecker` setup; knows the `Seed` / `BestSeed` track types. |

## 5. Consumers of seeds (not seeding itself)

- Matching: `Rec/Pr/PrAlgorithms/src/PrMatchNN.cpp`
- Downstream: `PrMatchNN_Downstream.cpp`, `PrDownStreamMatcher_UP_MP.cpp`, `PrDownTrack.h`
- Long-lived tracking: `PrLongLivedTracking.cpp`
- Kalman fit: `Rec/Tr/PrKalmanFilter/`
- MC checking: `Rec/Pr/PrMCTools/src/PrChecker.cpp`, `PrCheatedSciFiTracking.cpp`

## Not verified
- The internals of each function; only the structure of `PrHybridSeeding::operator()` was read.
- Which Moore options actually enable seeding for a given job.
