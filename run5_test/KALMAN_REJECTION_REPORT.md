# SciFi Kalman fit: code path and measured losses

Measured on 2026-11-11 with the already built local stack, using the baseline
Run 5 DIGI file and its first 20 events. No rebuild or production-code edits.

## How the SciFi seeds enter the fit

Run 5 uses `RecoConf.upgrade2_track_fitting.fit_tracks`, which configures
`TrackEventFitter` or `TrackEventFitterFuture` with `get_track_master_fitter`.
This is `TrackMasterFitter` with `TrackKalmanFilter` as its node fitter;
it is a different path from the `PrKalmanFilter` described in KALMAN_CODE_SUMMARY.md.

1. `get_pr_ft_tracks()` runs `make_PrHybridSeeding_pr_tracks()` and
   `fromPrSeedingTracksV1Tracks`. Conversion supplies FT hit IDs and initial
   `(x, y, tx, ty, q/p)` states.
2. For long tracks, `make_PrMatchNN_tracks(tv_tracks, ft_tracks)` passes the
   SciFi seeds as `PrMatchNN.SeedInput`. The matcher uses the seed EndT state,
   copies FT hit IDs, combines TV and seed states, and estimates momentum.
   `fromPrMatchTracksV1Tracks` converts the matched tracks.
3. `fit_tracks(..., {"TV": ..., "FT": ft_tracks["Clusters"]})` fits those
   matched tracks (see `get_upgrade2_hlt2_tracks`, `Match_FT_Fitted`). The
   diagnostic FT-only job instead fits the standalone converted seeds.
4. `TrackEventFitter::operator()` validates the input and invokes the fitter.
   `TrackMasterFitter::fit_r()` calls `makeNodes()`, whose
   `initializeRefStates()` uses the input states. The measurement provider loads
   hits by their IDs; `FTMeasurementProvider::addToMeasurements()` reconstructs
   spatial measurements from FT clusters and geometry. The seed's fitted curve
   is therefore an initial trajectory, while the Kalman fit refits measurements.
5. `TrackMasterFitter::fit_r()` calls `TrackKalmanFilter::fit()` iteratively,
   updates reference trajectories, removes outlier measurements through
   `outlierRemoved()`, and calls `determineStates()` for output states.
   `UseSeedStateErrors=False` supplies fresh seed covariance in this configuration.
6. `TrackEventFitter::operator()` omits failed fits and applies its own
   `MaxChi2DoF` (default 9999999 here). Later `select_tracks()` uses
   `TrackBestTrackCreator` and a separate quality cut; the merged long-track
   Run 5 configuration uses 7.5. These later losses must be counted separately.

## FT-only measurement

Run from `scifi_run5_work/run5_test`:

```bash
../../Moore/run gaudirun.py ../run5_ft_kalman_test.py > log_ft_kalman.txt 2>&1
```

Both baseline and FT-only fit jobs exited successfully.

| Counter | Total |
|---|---:|
| Events | 20 |
| Input SciFi seeds (`nTracks`) | 4723 |
| Successfully fitted (`nFitted`) | 4723 |
| Invalid input (`nBadInput`) | 0 |
| Fit failure rate | 0% |
| Output tracks, confirmed by converter and checker | 4723 |
| Removed outlier measurements (`numOutliers`) | 1842 |
| Tracks with fit probability below 0.01 (`badChisq`) | 125 |

Track rejection fraction: `(4723 - 4723) / 4723 = 0%`.
The 1842 removed measurements are hits, not killed tracks. The 125 low-probability
fits also survive this job. This diagnostic applies no tight post-fit selection.
Baseline and fitted samples both contain 643 ghosts (13.61%).

This is an observed result for standalone SciFi seeds in this sample, not a
universal rejection rate or a measurement of losses specifically caused by FT
measurements in a multi-detector fit.

## Matched long-track attempt

```bash
../../Moore/run gaudirun.py ../run5_ft_matched_kalman_test.py > log_ft_matched_kalman.txt 2>&1
```

This diagnostic builds TV + SciFi matches, fits them, and requests a subsequent
7.5 chi2/ndf selection. It exited with status 139, with
`TUnixSystem::DispatchSignals FATAL segmentation violation` while processing the
first input event. No completed fit counters were produced. The log does not
identify the crashing function, so this does not establish that the fitter itself
crashed. The matched long-track rejection fraction remains unmeasured.
