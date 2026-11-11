# Kalman fit in this repo (Rec/Tr/PrKalmanFilter)

Based on reading the code. Line numbers refer to the checked-out Rec (HEAD `914256b466`) and may shift.
Not read: the extrapolator implementation (`ITrackExtrapolator`), the `Node` class (`Event/PrFitNode.h`, where
`project_reference` is defined), `computeNoiseAndDeltaE`. Those parts are described only from how they are called.
Nothing here was measured; no run with the Kalman fit disabled exists.

## Files

| File | Role |
|---|---|
| `Rec/Tr/PrKalmanFilter/include/PrKalmanFilter/KF.h` (1418 lines) | The filter itself: node creation, predict, filter, fit, smoothing, iteration, outlier removal, output tracks |
| `Rec/Tr/PrKalmanFilter/src/KalmanFilter.cpp` | Gaudi algorithm, templated per track type; properties and track loop |
| `Rec/Tr/PrKalmanFilter/src/KalmanFilterTool.cpp` | Tool version of the same fit (per-track API); node building for VP/FT/UT/Muon |
| `Rec/Tr/PrKalmanFilter/src/V1V1PrKalmanFilter.cpp`, `ToolExample.cpp` | Not read |
| `Moore/Hlt/RecoConf/python/RecoConf/hlt2_tracking.py` | Wrappers and wiring (`make_PrKalmanFilter_*_tracks`) |

## State and measurement

- State: 5 parameters `(x, y, tx, ty, q/p)`. `q/p` is charge over momentum; `tx, ty` are the slopes dx/dz, dy/dz.
- One node per hit. No time in any node: FT node is `Node(x, 0, z, dxdy, 1, dzdy, ft_err(w), FTHit, lhcbid)`
  (`KF.h:199`, `KalmanFilterTool.cpp:163`).
- Hit errors: `ft_err(w) = 0.5/sqrt(w)` (`KF.h:65`); `vp_err = 0.0125` (`KF.h:66`); `ut_err(w)` (`KF.h:59`).
  `w` is the per-cluster weight (inverse variance), looked up as `invClusRes2[clus.pseudoSize()]`
  in `PrStoreSciFiHits.cpp`, so it exists only after clustering.
- Node fields used by the filter: `transport_matrix` (F), `transport_vector`, `noise_matrix`, `delta_energy`,
  `projection`, `ref_residual`, `measurement_error`, `predicted/filtered_state_vec/cov[forward|backward]`,
  `final_state_vec/cov`, `delta_chi2[...]`, `m_is_outlier`.

## Algorithm steps in `KF.h`

| Step | Function | Line (approx.) | What it does |
|---|---|---|---|
| 1 | `sort_hits_prepare_fitnodes` | 165 | Sorts hits, builds nodes from hit x, z, dxdy, dzdy and error |
| 2 | `init_nodes` | 395 | Propagates a start state through all nodes with the extrapolator; sets reference states, F, transport vector, `noise_matrix`, `delta_energy` (scattering and energy loss) |
| 3 | `KF::pre_fit_init` | 486 | Sets seed covariance diagonal from `varianceX/Y/Tx/Ty/QoP` |
| 4 | `KF::predict` | 503 | `x_pred = F * x_prev + transport_vector`; `C_pred = F C Fᵀ + noise_matrix` (backward pass uses F⁻¹) |
| 5 | `KF::filter` | 529 | `LHCb::Math::Filter` updates state with one hit using `projection`, `ref_residual`, `measurement_error²`; returns Δχ² with 1 dof |
| 6 | `KF::fit` | 586 | Forward pass, then backward pass from the forward result; returns the smaller χ². `smooth_and_update_ref_vector` (609) combines for the final state |
| 7 | `KF::iterate_fit` | 794 | Updates reference from smoothed result, recomputes transport (`update_transport_matrix`, 769), refits; stops when Δχ² < `0.01 * nDoF` or `max_fit_iter`; rejects if χ²/ndf >= `maxchi2perdof_pre_outlier` |
| 8 | `KF::remove_outliers` | 850 | Picks the node with the largest `ref_residual² / (V − HCH)`; flags it if above `min_chi2_for_outlier`; refits; never removes below the per-detector minimum layers; final cut χ²/ndf >= `maxchi2perdof` |

Other helpers in `KF.h`:
- `average_node` (556): averages forward and backward results when a node was skipped.
- `classical_smoother_iteration_for_alignment` (644).
- `get_upstream_seed` (280) and `get_downstream_seed` (335): initial states for those track types.
- `add_fitted_states` (983): fitted states on the output track, including RICH states.
- `make_output_track` and `add_output_v3_track` (1193–1300).

## Algorithm properties (`KalmanFilter.cpp`)

| Property | Default (C++) | Line | Moore default |
|---|---|---|---|
| `ErrorX`, `ErrorY` | 20 mm | 117, 118 | not checked |
| `ErrorTx`, `ErrorTy` | 0.1 | 119, 120 | not checked |
| `ErrorQoP` | 0.01 | 121 | not checked |
| `MaxChi2` | 9999999 | 123 | 2.8 (`hlt2_tracking.py` ~588) |
| `MaxChi2PreOutlierRemoval` | 9999999 | 126 | 20 (~589) |
| `MinChi2Outlier` | 9 | 124 | 9 (~590) |
| `MaxFitIterations` | 10 | 128 | not checked |
| `MaxOutlierIterations` | 2 | 129 | not checked |
| `MinNumVP/UT/FT/MuonHitsForOutlierRemoval` | 3 / 3 / 6 / 4 | 134–137 | not checked |
| `VeloTrackPT`, `MagOff`, `ClassicSmoothing`, `FillFitResult` | 400, false, false, false | 115–132 | not checked |

Counters: `chi2 cut` (144), `Pre outlier chi2 cut` (150). Track loop at lines ~167–267; a track is skipped
(not in the output) when the fit fails (228) or `remove_outliers` returns false (230–232).

## Variants (`KalmanFilter.cpp:297–320`)

| Algorithm | Track type | Hits | Output |
|---|---|---|---|
| `PrKalmanFilter_V1` | Long | VP+UT+FT | v1 tracks (also V3, V3Extra, V3Full) |
| `PrKalmanFilter_noUT_V1` | Long | VP+FT | same |
| `PrKalmanFilter_Downstream_V1` | Downstream | UT+FT | same |
| `PrKalmanFilter_Seed_V1` | Seed | FT only | T-tracks |
| `PrKalmanFilter_Velo_V1` | Velo | VP | Velo tracks |
| `PrKalmanFilter_Upstream_V1` | Upstream | VP+UT | Upstream tracks |

Only the Seed variant uses SciFi hits alone; four variants use SciFi hits.

## Place in the chain (`hlt2_tracking.py`)

1. Clustering: FT clusters, then `PrStoreSciFiHits` hit container.
2. Seeding: `PrHybridSeeding` (batch least-squares fit, no Kalman).
3. Other track building: `PrMatchNN` (Velo + seed), Forward tracking (Velo + FT hits), Downstream (seed + UT), VeloUT.
4. Clone killers: `PrCloneKillerLong`, `PrCloneKillerDown`, `PrCloneKillerSeed` (~1432–1522).
5. Kalman fits: `make_PrKalmanFilter_tracks` (582), `_noUT_` (630), `_Downstream_` (673), `_Upstream_` (716),
   `_Velo_` (759), `_Seed_` (799); used at ~1461–1632 and ~1715–1813.
6. `make_TrackBestTrackCreator_tracks` with `do_not_refit=True`, `fit_tracks=False`.

The Kalman fit does not match or build tracks; it refits tracks that matching, Forward or Downstream already made.
Matching quality comes from `PrMatchNN` (`MaxMatchChi2` 15, `MinMatchNN` 0.215, `MinMatchNN2` 0.95).
The fit can drop tracks through the `MaxChi2` cut and the outlier removal.

## Open points

- Fraction of tracks killed by the Kalman fit: not measured. The counters above would give it in one run.
- Which downstream tools read the covariance or fit χ²: not traced.
- Time in the Kalman fit: not implemented here; it would need a new node measurement row or state component and an extrapolator change.
