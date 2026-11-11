# SciFi timing seeding and seven-dimensional Kalman implementation

Scope: SciFi-only reconstruction. TV reconstruction is excluded. The MC checker can still unpack TV truth hits
to define reconstructibility categories; no TV measurements enter the fit.
No repository is pushed.

## Source provenance and configuration

The seeding source is ported from `jialu/Rec` commit `4fc746677b`, with the
velocity-normalization correction discussed in the design notes. It does not
restore the reverted `2012b47b2e` text-file prototype.

- `PrHybridSeeding` remains the spatial baseline.
- `PrHybridSeedingTiming` implements the jialu timing gates, intermediate time
  fits, and timing fields on seed output.
- `PrStoreSciFiTimeHits` is a separate MC-only producer, based on jialu's
  `PrStoreSciFiHits` changes. The ordinary spatial producer keeps its original
  input dependencies and does not require MC truth.
- LHCb `PrSciFiHits::HotInfo` gains an optional timestamp (default NaN).
  `PrSeedTracks` gains Time, ErrTime, and TimeChi2PerDoF fields.
- Moore removes the old `PrFTHitTimesFromFile` wiring and exposes explicit
  opt-in timing builders.

## Sample timing: what is and is not present

The directory
`/eos/lhcb/wg/rta/WP6/UII/Jan2026/MINBIAS/1p3E34/`
contains extended DIGI files, including
`MINBIAS_proto-v00.03_L1p3E34_Slot_9-30000000-100ev-20260129-Extended.digi`.

The code's FTLiteCluster representation contains a channel ID, fraction and
cluster size, not a measured timestamp. The port obtains MCHit::time through
`Link/Raw/FT/LiteClusters2MCHits`. This is truth-derived timing, not an assertion
that this sample already contains smeared detector timestamps.

The explicit default readout model is:

```text
t_readout = t_MC + Gaussian(0, sigma_ns) + |y_MC_mid| / fibre_speed
sigma_ns = 0.8 ns
fibre_speed = 150 mm/ns
```

It reproduces the inspected jialu implementation. In particular, it is not
`(Y_readout-|y|)/speed`, despite stale comments in the source snapshot. Smearing
is introduced once by this producer. Disabling the readout model gives unsmeared
MCHit passage times; the fitter then requires FibreSpeed=0 and a deliberate
choice of timing measurement uncertainty.

The port retains jialu's MC-hit selection: up to two times can be associated
with one cluster. The Kalman component does not guess which is correct: IDs
with multiple finite time entries receive a spatial-only update.

The production overview at
`/eos/lhcb/wg/rta/WP6/tdr_u2_august2026/readme.md` says extended DIGI contains
MCHits from all subsystems. It distinguishes middle, RICH-updated, and lower
geometries. For example:

```text
middle-scenario-july2026_1p3e34/MINBIAS/boole/
    MINBIAS_30000000_1p3e34_slot_0_100-Extended.digi
```

Do not run these newer geometry scenarios with the January geometry by simply
changing the input filename. The smoke test below uses the January file and
its matching `proto-v00.03-picocalfix` geometry. No additional smearing claim is
inferred from the production directory names or README.

The seed's stored Time is the intercept of its time-versus-z fit. When input
includes fibre delay, that intercept and effective fitted speed should not be
interpreted directly as particle passage time/velocity or production time. The
7D fitter instead defines t as particle passage time and includes fibre delay
explicitly in the measurement prediction; it does not reuse seed timing as an
independent prior.

## Seven-dimensional fit

`Rec/Tr/TrackFitter/src/SciFiTimeKalman.{h,cpp}` implements an opt-in Gaudi
algorithm and a separately testable numerical core. State order and units:

```text
(x[mm], y[mm], t[ns], tx, ty, v[mm/ns], q/p[existing units])
```

The common five-dimensional LHCb State API is unchanged. The component fits
all seven quantities jointly and keeps all seven-dimensional covariances
internally; output v1 tracks contain the spatial marginals and the full
reference posterior in extraInfo (schema below). This avoids changing every
shared extrapolator, projector, and downstream track consumer at once.

Processing:

1. Run TrackMasterFitter to obtain a reference trajectory, spatial projections,
   and material noise. Moore disables its outlier removal for this use.
2. Start the 7D fit with broad independent uncertainties. Do not reuse the
   spatial prefit's posterior covariance or seed time covariance as another
   prior on the same measurements.
3. Recompute spatial transport with the configured extrapolator and existing
   deterministic energy-loss convention. Copy the material Q block from the
   reference fit.
4. Propagate t using a signed trapezoidal path-length approximation divided by
   fitted v. Its Jacobian includes velocity, direction, and the derivatives of
   the propagated spatial direction. Velocity is constant across the track;
   it is not calculated from a mass or q/p.
5. Update the existing one-dimensional spatial fibre measurement and the
   independent timing observation sequentially. The timing row includes the
   derivative of |y|/fibre_speed. For corrected passage times, FibreSpeed=0.
6. Use Joseph covariance updates and Rauch–Tung–Striebel smoothing. Iterate
   reference states and spatial projections/transports; each pass resets the
   same original prior and uses each retained measurement once.
7. Optionally remove up to MaxTimeOutliers (default 2) timing observations with
   biased residual chi2 above TimeOutlierChi2 (default 9), retaining at least
   three timed observations and retaining their spatial measurements.
8. Emit spatial marginals and full reference timing/covariance. Clear the
   ordinary KalmanFitResult because its cached values describe the prefit.

With UseTime=False, the algorithm returns the ordinary spatial fit. With fewer
than three usable timestamps, it records a spatial fallback rather than
inventing a time constraint. Non-FT inputs are rejected. Fit failures and
fallbacks are separate counters.

Chi2 counts spatial and retained timing observations. The effective spatial
parameter count comes from TrackMasterFitter; two timing parameters are added.
A seven-component state does not automatically mean seven constrained degrees
of freedom.

### Output extraInfo schema, version 1

Keys are local experimental keys, not new values in the common AdditionalInfo
enum. Read them by casting the integer key. Consumers must check key 61002.

| Key | Value |
|---|---|
| 61000 | Reference z [mm], the first node in filtering order |
| 61001 | Number of retained timing observations |
| 61002 | Schema version = 1; absent for spatial fallback |
| 61010 + a | State component a, ordered `(x,y,t,tx,ty,v,q/p)` |
| 61100 + a*(a+1)/2 + b, b <= a | Lower-triangular full covariance C[a,b] |

The reference node is not necessarily the first state in the track's sorted
state list. Always use the recorded reference z. Generic v1→future converters
do not preserve this experimental 7D schema: retain the v1 output when studying
timing and its correlations. The test's future conversion is for the existing
spatial MC checker only. MC links are built from that final dense future
container, because rejected v1 tracks leave gaps in the original track keys.

## Running

Build/install the modified projects in dependency order. The shared hit and
seed layout changed, so consumers must be rebuilt together; do not load old
libraries compiled against the previous layout.

From a test output directory, for example `scifi_run5_work/run5_test`:

```bash
../../Moore/run gaudirun.py ../run5_scifi_time_kalman_test.py > log_scifi_time_7d.txt 2>&1
```

Settings come from `./scifi_time_config.json`, because Moore/run does not
reliably preserve caller environment variables. Example:

```json
{
  "events": 20,
  "sigma_ns": 0.8,
  "readout_model": true,
  "fibre_speed": 150.0,
  "time_seeding": true,
  "time_kalman": true,
  "fit": true,
  "tag": "scifi_time_7d"
}
```

- `time_seeding=false`: baseline spatial seeding with the same MC timing input.
- `time_kalman=false`: ordinary spatial fit, useful as a control.
- `fit=false`: seeding-only diagnostic.
- `input_file` and `geometry`: explicit sample/geometry overrides.

For a fair fit comparison, hold the seeding configuration and event sample
fixed while toggling time_kalman. The timing and baseline seeding algorithms
have different candidate-search flows, so switching time_seeding also changes
more than just the fit.

## Numerical tests

Standalone (no Gaudi runtime needed):

```bash
/usr/bin/g++ -std=c++17 -O2 -Wall -Wextra -pedantic \
  Rec/Tr/TrackFitter/tests/test_SciFiTimeKalman.cpp -o /tmp/test_scifi_time_kalman
/tmp/test_scifi_time_kalman
```

The same test is registered with CMake as `test_SciFiTimeKalman`. It checks
scalar gain/chi2, covariance inversion across very different units, finite-
difference timing transport derivatives, reverse propagation, smoothing,
independently fitted velocity, spatial/time coupling, and the seeding velocity
normalization correction and timing/velocity pull coverage on 128 noisy tracks.

## Approximations and remaining physics validation

This is an experimental FT-only fit, not a validated production replacement.
Velocity is constant; material noise is frozen from the spatial reference fit,
with no additional timing Q. Path length uses endpoint directions rather than
an exact integral along the Runge–Kutta trajectory. Timing noise is independent
between hits. Shared-clock calibration correlations are not modelled.

Validate residuals and pulls on realistic samples, both detector halves,
missing/ambiguous timing, outliers, momentum tails, efficiency, and runtime.
The standalone tests establish numerical behavior, not an improvement in
physics performance. Free velocity supplies no mass–momentum constraint.


## Local commit checks

Repository hooks are run when committing. The Moore-only `wrap-pid-conditions`
hook requires a new libcst environment that could not be installed because
PyPI name resolution is unavailable in this execution environment. That hook
is skipped for these tracking configuration changes; the other Moore hooks
(including Ruff) run normally. Rec and LHCb hooks run normally. Hook cache
writes use `/tmp/xihu/pre-commit` because the default user cache is read-only.


## ROOT access in this execution environment

ROOT.TFile.Open crashes on the direct EOS-mounted January sample path here,
including outside Gaudi. The same file opens successfully after copying it to
`/tmp/xihu/scifi_1p3_slot9.digi`. Validation JSON files therefore select that
local copy. `run5_time_validation/sample.sha256` records both checksums.
To reproduce after the temporary cache expires, copy the source again:

```bash
mkdir -p /tmp/xihu
cp /eos/lhcb/wg/rta/WP6/UII/Jan2026/MINBIAS/1p3E34/MINBIAS_proto-v00.03_L1p3E34_Slot_9-30000000-100ev-20260129-Extended.digi /tmp/xihu/scifi_1p3_slot9.digi
```

Set `input_file` in scifi_time_config.json to that local path. No sample data is
committed. The script's default retains the original EOS source location.


## Recorded validation

See [run5_time_validation/VALIDATION_REPORT.md](run5_time_validation/VALIDATION_REPORT.md)
for the completed 20-event controls and joint-fit run, final counters, input
checksum and pinned code revisions. These results do not establish improved
physics resolution or optimized selection efficiency.
