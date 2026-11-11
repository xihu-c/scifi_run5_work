# SciFi timing implementation: validation report

Date: 2026-11-11. All four runs processed the first 20 events of the January
1.3e34 minimum-bias DIGI sample, using the same explicit MC timing model:
0.8 ns independent Gaussian smearing plus |y_MC_mid|/150 mm/ns fibre delay.
TV reconstruction is not run. MC truth hits from other detectors may be
unpacked solely for reconstructibility categories.

## Build and numerical checks

- Full affected Rec consumer build and install completed successfully.
- The final TrackFitter module rebuild completed successfully.
- CTest `TrackFitter.test_SciFiTimeKalman` passed. The test covers the update,
  covariance inversion/scaling, transport Jacobians, reverse transport,
  smoothing, free velocity recovery, time-space coupling, seed velocity
  normalization, and timing/velocity pull coverage on 128 noisy tracks.
- LHCb and Rec commit hooks passed. Moore hooks passed except the unrelated
  PID-rewriting hook, whose libcst environment could not be installed without
  network resolution; that hook was explicitly skipped.

## Event-level results

| Configuration | Fit inputs (or seeds) | Output tracks | Ghosts | Long FT-reconstructible efficiency |
|---|---:|---:|---:|---:|
| Spatial seeding + spatial fit | 6873 | 6873 | 1769 (25.74%) | 89.00% |
| Timing seeding only | 4610 | 4610 | 122 (2.65%) | 80.25% |
| Timing seeding + spatial fit | 4610 | 4610 | 122 (2.65%) | 80.25% |
| Timing seeding + 7D fit | 4610 | 4569 | 110 (2.41%) | 80.05% |

Every run exited with status 0 and reported successful application termination.
“Long FT-reconstructible” is the MC checker category, not reconstructed TV+FT
long tracks. The fit input is FT-only in all fitted cases.

### Seven-dimensional fit

- Input tracks: 4610.
- Successful timed fits: 4569.
- Rejected fits: 41 (0.89%).
- Spatial fallbacks: 0; every output track used timing.
- Retained time measurements: 44295.
- Removed time measurements: 349; their spatial
  cluster measurements remain in the fit.
- Mean fitted velocity: 309.70 mm/ns.
- Mean reference-time uncertainty: 1.8585 ns,
  at the stored reference plane, not necessarily the SciFi midpoint or origin.

A diagnostic repeat attributed the 41 fit failures to 35 invalid velocity
estimates, five invalid posterior state/covariance estimates, and one singular
covariance. The final normal-log run also checks every exported node state and
variance and gives the same 41 failures. These are recorded fit failures, not
an established physics background-selection efficiency.

The implementation remains experimental. These checks establish runnable
integration and numerical behavior, not improved momentum or vertex resolution.
The two seeding algorithms also differ in candidate-search flow and hit
flagging; the first-versus-second row does not isolate timing alone. Cuts are
not optimized. All configurations use the same timed hit producer, including
its treatment of overlapping MC-hit links.

## Input access and reproduction

The direct EOS-mounted source caused ROOT.TFile.Open to crash before event
processing, even outside Gaudi. A complete local copy opens successfully.
Both files have SHA-256
`5c185cfbf681dd6e03950bf0843adb414f8c1e13df9e7d38c6d3c1c8af26c58f`.
See [sample.sha256](sample.sha256) for paths. No sample data is committed.

Each subdirectory contains its configuration and final log. After restoring
the cache as documented in [SCIFI_TIME_IMPLEMENTATION.md](../SCIFI_TIME_IMPLEMENTATION.md),
run from the desired case directory:

```bash
../../../Moore/run gaudirun.py ../../run5_scifi_time_kalman_test.py > log.txt 2>&1
```

The final MC associations are built from the converted future-track container.
This matters after fit rejection: v1 keys may contain gaps, while the converted
container uses dense indices. Associating the original v1 keys and applying
those links to the future container caused the initial checker crash; that
configuration bug is fixed in the test job.

Code revisions are pinned in [commits.json](commits.json). Detailed counters
are also available in [summary.json](summary.json). ROOT histogram/tuple files
are local artifacts and ignored by Git.
