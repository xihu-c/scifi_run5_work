# Proposal: time-aware seven-dimensional SciFi-only Kalman fit

Status: original design notes. An experimental implementation is described in
[SCIFI_TIME_IMPLEMENTATION.md](SCIFI_TIME_IMPLEMENTATION.md); production physics
validation remains outstanding. Scope: FT measurements and
SciFi-only tracks; TV reconstruction is excluded.

This extends the process described in
[SCIFI_SPATIAL_KALMAN_READING_GUIDE.md](SCIFI_SPATIAL_KALMAN_READING_GUIDE.md).
The starting implementation is `TrackMasterFitter` → `TrackKalmanFilter` →
`FitNode`, rather than `PrKalmanFilter`.

## 1. State: fit particle velocity independently

At a reference plane z, choose

```text
s(z) = (x, y, t, tx, ty, v, q/p)ᵀ
tx = dx/dz
ty = dy/dz
```

- t is particle passage time at the reference plane, not readout time or
  automatically production time.
- v is a fitted particle velocity, independent of q/p. It is not the fibre
  signal propagation speed.
- q/p retains its spatial-track meaning.

This follows the seeding idea of fitting two extra timing parameters instead
of calculating velocity from momentum and an assumed mass. It is a joint
seven-dimensional fit only when the measurement or transport model couples
the timing and spatial components.

An alternative state is `(x, y, t, tx, ty, tt, q/p)`, where

```text
tt = dt/dz = sqrt(1 + tx² + ty²) / v
```

The two parameterizations describe equivalent local information, but require
different transport rules. Constant v does not imply constant tt if direction
changes. All matrices and initial covariances must use the chosen
parameterization consistently.

Suggested initial units: x, y, z in mm; t in ns; v in mm/ns; tt in ns/mm;
momentum in the existing repository convention. Matrix entries consequently
have different physical units.

## 2. Transport and Jacobian F

Retain the spatial propagation model for `(x, y, tx, ty, q/p)` and extend it
with time propagation.

For constant v over one transport segment:

```text
t_j = t_i + L_ij / v_i
v_j = v_i
```

L_ij is signed path length along the physical direction of travel: it must
give the correct sign for both forward and reverse propagation. For a
forward-going particle and a straight segment:

```text
L_ij ≈ (z_j - z_i) * sqrt(1 + tx_i² + ty_i²)
```

Use the propagated trajectory for a more accurate path length. Essential
Jacobian entries include:

```text
F[t,t] = 1
F[t,v] = -L_ij / v_i²
F[v,v] = 1
F[t,a] = (1/v_i) * ∂L_ij/∂a
```

Here a denotes spatial state parameters that affect the path. Under the
straight-segment approximation, with k = sqrt(1 + tx² + ty²):

```text
F[t,tx] = Δz * tx / (v*k)
F[t,ty] = Δz * ty / (v*k)
```

The usual prediction remains

```text
s_j^- = f(s_i^+)
C_j^- = F_ij * C_i^+ * F_ijᵀ + Q_ij
```

The existing code represents locally linearized transport using a matrix and
offset. Extend both consistently; replacing only the matrix dimensions is
insufficient.

For the tt parameterization, the simplest approximation is

```text
t_j = t_i + tt_i * Δz
tt_j = tt_i
F[t,tt] = Δz
```

If constant physical velocity is intended, tt must instead change with the
path factor as the direction changes. A constant-tt model is an empirical
linear time-versus-z model, not an exact constant-speed model on a curved path.

## 3. Measurement vector and Jacobian H

Each FT cluster may provide two observations:

```text
m_i = (u_i, t_readout_i)ᵀ
```

The spatial observation u_i remains one-dimensional. For explanation, use

```text
h_u(s_i) ≈ x_i + alpha_i*y_i
```

The actual implementation must retain the existing fibre-trajectory projection
and its coordinate/sign conventions.

### Corrected particle timestamp

If the timing observation already represents particle passage time at the
node, the simplified measurement model and Jacobian are

```text
h(s_i) = (x_i + alpha_i*y_i, t_i)ᵀ

H_i = [ 1  alpha_i  0  0  0  0  0 ]
      [ 0     0     1  0  0  0  0 ]
```

There are two rows because there are two observations. The spatial row is
`(1, alpha_i, 0, 0, 0, 0, 0)`. A single row
`(1, alpha_i, 1, 0, 0, 0, 0)` would incorrectly represent adding spatial
position and time into one observation.

### Readout timestamp with fibre delay

Prefer an explicit calibrated measurement model when delay depends on the
unknown hit position:

```text
h_time(s_i) = t_i + tau_i(x_i,y_i) + delta_i

H_i = [       1          alpha_i     0  0  0  0  0 ]
      [ ∂tau_i/∂x_i    ∂tau_i/∂y_i   1  0  0  0  0 ]
```

tau_i is the signal propagation delay along the fibre; delta_i is a calibrated
channel offset. Derive the delay and its signs from the actual fibre geometry
and readout side. The simulation currently examined can add a delay
proportional to |y|; do not assume a different readout convention silently.

Velocity has no explicit entry in this local timing row because t is already
the particle time at the node. Velocity influences that time through F.
Different state reference positions or a finite-depth measurement model can
require additional measurement derivatives.

Correcting timestamps using a fitted position and then treating that correction
as exact can lose spatial/time correlations. Either include the delay in h,
or propagate correction uncertainty and correlation consistently.

## 4. Measurement covariance R

If spatial and timing measurement errors are independent:

```text
R_i = [ sigma_u_i²      0      ]
      [     0      sigma_t_i²  ]
```

Otherwise include their covariance. These are detector measurement variances,
not arbitrary fit penalties. Common clock or calibration uncertainties may
also correlate different hits; independent per-hit errors do not describe
those effects automatically.

Missing or unusable timing should leave a valid spatial-only update, with a
one-row H and scalar R. The two observations can be updated together, or
sequentially if their noise treatment and linearization are consistent.

## 5. Process noise Q

Q describes uncertainty introduced between nodes. Timestamp measurement
resolution belongs in R, not again in Q.

Retain the existing material model for the spatial block. For a first
deterministic constant-v timing model, the new timing process-noise block can
start at zero. This does not imply zero timing uncertainty: initial covariance,
measurement noise, and transport still contribute uncertainty.

If velocity changes are modelled, derive timing/velocity noise and cross terms
from that physical model. Scattering changes path length, and energy loss can
change velocity. Fitting v independently of q/p does not supply a law for those
changes automatically. Ignoring them is an explicit approximation to validate.

## 6. Initialization and covariance

Initialize a 7 × 7 covariance with sensible spatial and timing uncertainties.
The time intercept and fitted slope/velocity can be correlated; retain that
correlation when using an independently justified prior.

The seed time fit uses the same FT timestamps that the Kalman fit will process.
Use its result as an initial reference estimate without treating its covariance
as an additional independent constraint on those same observations. Otherwise
the data can be counted twice. Apply the same reasoning to spatial seed errors.

Free v requires physical/numerical handling of near-zero or negative values.
An inverse-speed parameter may simplify time propagation, but changes the
state definition and covariance transformations. Choose this explicitly.

## 7. Expected coupling and benefits

Putting spatial and timing parameters into the same vector does not alone
guarantee better momentum resolution.

- Fibre delay can couple timing to spatial coordinates through H.
- Path length couples timing to direction and potentially momentum through F.
- Timing can improve hit association and outlier decisions.
- A free v does not impose a mass–momentum relation. A direct time-of-flight
  momentum constraint would require an additional physical hypothesis.

If H, F, Q, and the initial covariance separate into independent spatial and
timing blocks, the result is mathematically two separate fits, regardless of
the combined state-vector size.

SciFi-only passage times do not by themselves determine production time and
production position independently. No TV or primary-vertex information is
assumed in this proposal.

## 8. Repository components to inspect or extend

Paths below are relative to the stack root:

| Component | Required consideration |
|---|---|
| State/state-vector and covariance types | Seven components, units, indexing, serialization and consumers |
| `Tr/TrackTools/src/FTMeasurementProvider.cpp` | Timestamp retrieval and uncertainty alongside spatial measurement |
| `Tr/TrackTools/src/MeasurementProviderProjector.cpp` | Time prediction, residual, H and fibre-delay derivatives |
| `Tr/TrackFitEvent/include/Event/FitNode.h` and `src/FitNode.cpp` | Extended state, measurement handling, prediction, filtering and smoothing |
| `Tr/TrackFitter/src/TrackMasterFitter.cpp` | Initialization, reference trajectory, transport, Q, iterations, outliers and output states |
| `Tr/TrackFitter/src/TrackKalmanFilter.cpp` | Fit orchestration and effective parameter/measurement counting |
| Kalman numerical helpers | Dimensions and supported measurement/state types |
| `Tr/TrackFitter/src/TrackEventFitter.cpp` and converters | Preserve fitted time and velocity; replace timestamp-copy logic consistently |
| Moore fitting configuration | Enable the timing model and expose its assumptions |

These files are under `jialu/Rec` for the inspected timing branch. Changes to
shared event/state definitions may also require work in LHCb. Extending shared
types has wider consequences than a local SciFi algorithm change; an isolated
prototype may be useful before changing common interfaces.

## 9. Validation sequence

1. With timing disabled, reproduce the existing spatial fit.
2. Check transport and measurement Jacobians against numerical derivatives.
3. Use straight synthetic tracks with known t and v; verify recovery and pulls.
4. Verify forward/reverse transport and smoothing consistency.
5. Add the fibre-delay model and check both detector halves.
6. Verify uncertainty coverage, including time–velocity correlations.
7. Count scalar observations and genuinely constrained parameters correctly
   when reporting chi-squared per degree of freedom. Do not always subtract
   seven merely because the state has seven entries.
8. Define whether outlier removal drops only a bad timestamp or the entire
   cluster, and validate both efficiency and bias.
9. Compare the same simulated events with timing enabled/disabled: efficiency,
   ghosts, momentum residuals and tails, time/velocity residuals, pulls, fit
   failures, outliers and runtime. Separate changes in selected track population
   from parameter improvements for tracks common to both samples.

## 10. Known seeding detail to resolve before reusing its velocity

In the inspected `PrSciFiXZTimeFit.h`, `fitN()` regresses time against
`x = (z-z0)*pathFactor`. Its fitted slope m therefore corresponds to 1/v for
the documented model. The code stores `velocity = pathFactor/m`, while
`tAt()` uses `(z-z0)*pathFactor/velocity`. Consequently `tAt()` does not
reproduce the regression prediction when pathFactor differs from one.

Check and resolve that normalization before treating the existing fitted
velocity as a physical initial value. This proposal does not modify that code.
