# Reading guide: the SciFi-only spatial Kalman fit

Follow one SciFi-only track from seed to fitted output. Learn prediction and
measurement update first, then smoothing, material effects, and outlier removal.
TV reconstruction is outside this study.

## Scope and code versions

The C++ references below use `jialu/Rec`, at commit `4fc746677b` when this guide
was written. Paths are relative to this document. The earlier successful FT-only
test used the built top-level `Rec`; line numbers and configurations differ.

The existing `KALMAN_CODE_SUMMARY.md` primarily describes `PrKalmanFilter`.
The FT-only diagnostic instead uses:

```text
TrackEventFitter → TrackMasterFitter → TrackKalmanFilter → FitNode
```

The runnable diagnostic is [run5_ft_kalman_test.py](run5_ft_kalman_test.py).
Its measured results are in
[KALMAN_REJECTION_REPORT.md](run5_test/KALMAN_REJECTION_REPORT.md).

## 1. What is being estimated?

At each reference position z, the Kalman state is

```text
s(z) = (x, y, tx, ty, q/p)ᵀ
tx = dx/dz
ty = dy/dz
```

It also carries a 5 × 5 covariance matrix C:

- Diagonal elements describe parameter variances.
- Off-diagonal elements describe correlations, for example between position
  and slope.

These parameters differ from the seeding polynomial parameters
`(ax, bx, cx, ay, by)`. The converter turns the seed into local states suitable
for propagation.

Read [fromPrTracksV1Track.cpp](../jialu/Rec/Pr/PrConverters/src/fromPrTracksV1Track.cpp),
especially `ConvertTrack()` around line 195: hit-ID copying and state creation.

**Checkpoint:** identify which information comes from the seed: hit IDs,
positions, slopes, and estimated q/p.

## 2. Read the configuration before the C++

Read
[upgrade2_track_fitting.py](../jialu/Moore/Hlt/RecoConf/python/RecoConf/upgrade2_track_fitting.py):
`get_track_master_fitter()` around line 56, then `fit_tracks()` around line 157.

For the SciFi-only case, supply:

```python
fit_tracks(seed_tracks, {"FT": ft_clusters})
```

The provider configuration ignores detectors absent from that dictionary.
Notice `UseSeedStateErrors=False`: the seed supplies the initial trajectory,
but the fitter initializes its own covariance.

Next, read `TrackEventFitter::operator()` around line 129 in
[TrackEventFitter.cpp](../jialu/Rec/Tr/TrackFitter/src/TrackEventFitter.cpp).
This is the event-level wrapper: it checks inputs, calls the fitter, counts
failures, and writes surviving tracks.

**Checkpoint:** distinguish an initial trajectory from a statistical constraint.
Reusing the seeding covariance as an independent measurement could count the
same hit information twice.

## 3. What does one SciFi measurement mean?

Read `FTMeasurementProvider::addToMeasurements()` around line 56 in
[FTMeasurementProvider.cpp](../jialu/Rec/Tr/TrackTools/src/FTMeasurementProvider.cpp).

For each FT hit ID, it finds the cluster and constructs a measurement from its
fibre trajectory, geometry, and uncertainty.

**One SciFi hit gives one spatial constraint**, rather than separate
measurements of x and y. X layers mainly constrain x; stereo layers constrain
a combination of x and y.

For intuition, approximate the measurement as

```text
u_i ≈ x(z_i) + alpha_i * y(z_i)
H_i = ∂u_i/∂s ≈ (1, alpha_i, 0, 0, 0)
```

Here `alpha_i` represents the layer orientation. This is an explanatory
approximation; the actual implementation uses track-to-fibre geometry and a
distance of closest approach, with its own sign conventions.

Read `MeasurementProviderProjector::projectReference()` around line 78 in
[MeasurementProviderProjector.cpp](../jialu/Rec/Tr/TrackTools/src/MeasurementProviderProjector.cpp)
for how it stores the residual, measurement error, and projection matrix.

**Checkpoint:** a hit need not measure momentum directly to influence momentum
through correlations and propagation.

## 4. Read the main orchestration function

Open `TrackMasterFitter::fit_r()` around line 180 in
[TrackMasterFitter.cpp](../jialu/Rec/Tr/TrackFitter/src/TrackMasterFitter.cpp).

On the first pass, follow only this sequence:

```text
makeNodes()
initialize seed covariance
repeat:
    update reference trajectory and transport as configured
    TrackKalmanFilter::fit()
remove outliers and refit
determineStates()
mark success or failure
```

Then read `makeNodes()` around line 612 in the same file.

A **node** is a position along the trajectory that stores information needed
for filtering. Measurement nodes contain hits. Additional reference nodes
request states at useful locations without adding a measurement.

Notice that nodes can be sorted in **decreasing z**. “Forward filter” means
forward through the node sequence, not necessarily increasing z.

## 5. The two central Kalman operations

The mathematical work is largely inside `FitNode`, rather than inside the
short `TrackKalmanFilter::fit()` function.

### Prediction

Read `FitNode::computePredictedState()` around line 274 in
[FitNode.cpp](../jialu/Rec/Tr/TrackFitEvent/src/FitNode.cpp).

Prediction transports the previous estimate to the next node:

```text
s_i^- = F_i * s_(i-1)^+ + b_i
C_i^- = F_i * C_(i-1)^+ * F_iᵀ + Q_i
```

| Symbol | Meaning |
|---|---|
| F_i | Derivative of propagation with respect to the previous state |
| b_i | Offset needed for the locally linearized propagation |
| Q_i | Uncertainty added by material effects |
| Superscript − | Before using the current hit |
| Superscript + | After using the current hit |

The code also handles reverse propagation and initialization; start by
understanding the ordinary forward prediction branch.

### Measurement update

Read `computeFilteredState()` around line 327 in the same file. It calls
`LHCb::Math::Filter`.

For a scalar measurement, the standard update is

```text
r_i = u_i - h(s_i^-)
S_i = H_i * C_i^- * H_iᵀ + R_i
K_i = C_i^- * H_iᵀ / S_i

s_i^+ = s_i^- + K_i * r_i
C_i^+ = C_i^- - K_i * H_i * C_i^-
```

`R_i` is measurement variance. `S_i` is the innovation variance. The Kalman
gain `K_i` determines how strongly the hit changes each state parameter.
For a scalar innovation, its chi-squared contribution is `r_i² / S_i`.

The code expresses this update around a reference trajectory, using
`refVector`, `refResidual`, and `projectionMatrix`. Match those quantities to
the equations before following the numerical implementation further.

### Small exercise

Suppose predicted x and measured x both have uncertainty 0.1 mm. Their scalar
Kalman gain is 1/2. A measured displacement of 0.2 mm shifts the estimate by
0.1 mm. The updated variance is 0.005 mm², giving uncertainty about 0.071 mm.

In five dimensions, correlations let that same hit also update slopes and
possibly q/p.

**Checkpoint:** explain why a very uncertain measurement produces a small
update, and why a precise measurement produces a stronger update.

## 6. Smoothing and repeated fitting

Read `TrackKalmanFilter::fit()` around line 36 in
[TrackKalmanFilter.cpp](../jialu/Rec/Tr/TrackFitter/src/TrackKalmanFilter.cpp),
then `computeBiSmoothedState()` around line 395 in
[FitNode.cpp](../jialu/Rec/Tr/TrackFitEvent/src/FitNode.cpp).

Filtering at a node uses information encountered from one direction.
**Smoothing incorporates information from both sides**, producing an estimate
at that node using the whole track. The implementation combines a filtered
estimate from one side with a predicted estimate from the other to avoid using
the local hit twice.

The outer iterations in `fit_r()` solve another problem: propagation and
projection are nonlinear. After obtaining improved states, the fitter updates
its reference trajectory, recalculates the linear approximation, and fits again.

The state accessors use cached computations. Asking for `predictedState()`,
`filteredState()`, or a smoothed state can trigger the corresponding calculation.
This explains why the orchestration function contains relatively little algebra.

## 7. Physical corrections and rejection logic

Return to these functions in
[TrackMasterFitter.cpp](../jialu/Rec/Tr/TrackFitter/src/TrackMasterFitter.cpp):

- `updateTransport()` around line 823 constructs F and the transport offset,
  including the momentum correction from energy loss.
- `updateMaterialCorrections()` around line 719 prepares material noise and
  energy-loss information.
- `outlierRemoved()` around line 431 selects an inconsistent measurement for
  removal, subject to minimum-hit requirements.
- `determineStates()` around line 354 constructs output states at the requested
  positions.

For SciFi-only tracks, pay particular attention to `updateTransport()` checking
whether propagation depends on q/p. A five-component state does not guarantee
five strongly measured parameters. The code can account for four effective
fitted parameters when momentum is not constrained; `TrackKalmanFilter::fit()`
also examines the momentum covariance.

Keep three operations distinct:

1. Removing an outlier **hit** and refitting the track.
2. Rejecting a **track** because fitting failed.
3. Rejecting a successfully fitted track with a subsequent quality cut.

The earlier FT-only test fitted all 4,723 input seeds successfully while
removing 1,842 outlier measurements. Those measurements were not killed tracks.

## Suggested first reading session

Concentrate on sections 1–5. For one FT hit, explain:

1. What state was predicted at the hit?
2. What one-dimensional quantity was measured?
3. How were prediction and measurement uncertainties combined?
4. Why can a one-dimensional measurement change several state parameters?

That is the foundation needed before introducing a time measurement. Later,
time integration will require examining the state definition, measurement model,
projection derivatives, transport, covariance, and output handling together.
This guide describes the current spatial process; it does not implement that
extension.
