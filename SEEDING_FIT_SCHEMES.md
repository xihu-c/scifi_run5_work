# SciFi seeding fits: original (5 par.) and proposed time-aware schemes (6 / 7 par.)

Self-contained summary. No prior knowledge of our session is assumed.
Code references are in `Rec/Pr/PrAlgorithms/src/` (`PrHybridSeeding.cpp`, `PrHybridSeedTrack.h`,
`PrTrackFitter{XZ,YZ,XYZ}.h`). Hit creation: `PrStoreSciFiHits.cpp`.

**Status:** the original scheme is what the code does today. The 6- and 7-parameter schemes are
*proposals* (nothing implemented). It is not yet verified that Run 5 SciFi hits carry a time or what its
resolution is; every `sigma_t` below is a placeholder.

---

## 0. Detector and notation

**Layout** (`FTConstants.h`, `FTChannelID.h`, geometry `FT proto-run5-v00.01`, `parameters.xml`):
3 stations (T1,T2,T3) x 4 layers in the order X1, U, V, X2, i.e. 12 layers:
6 x-layers (angle 0), 3 U-layers (-5 deg), 3 V-layers (+5 deg). No layer measures y directly.

**Each hit i is one 1-D measurement** `u_i` in layer l(i) at known z_i:

    u_i = x_i^0 + y_i * dxdy_l ,       dxdy_l = 0 (X),  tan(theta_l) with theta = -5 or +5 deg (U,V)

(`x_i^0` is the hit position at y=0, `dxdy` the layer slope; in the code `sciFiHits.x(i, y)` and `dxdy`.)
So a seed with N hits has N position measurements, not 3N. y enters only through stereo layers.

**Position uncertainty** (`PrStoreSciFiHits.cpp`, hard-coded, depends on cluster size `pseudoSize`=0..8):

    sigma_x = 0.05, 0.08, 0.11, 0.14, 0.17, 0.20, 0.23, 0.26, 0.29   (mm presumably),   w_i = 1/sigma_x^2

For a stereo hit the information on y is `sigma_y ~ sigma_x / tan(5 deg) ~ 11.4 sigma_x`.

**Reference z:** `z_ref = ZMidT = 8520 mm`, `dz = z - z_ref`.

**Particle:** slopes `tx = dx/dz`, `ty = dy/dz`, `k = sqrt(1 + tx^2 + ty^2)`, speed `beta c`,
`c = 299.792 mm/ns` (1/c = 3.3356 ps/mm).

---

## 1. Original scheme: 5 parameters, space only (what the code does)

### Track model (`PrHybridSeedTrack.h`)

    x(z) = ax + dz * ( bx + dz * cx * (1 + dRatio * dz) )          (parabola + small cubic term)
    y(z) = ay + by * dz                                            (straight line)

`dRatio` is **not** a free parameter. It is a fixed constant (default -0.000262) in the x-z search and
parameterised in the final fit by `dRatioPar = {0.000267957, -8.651e-06, 4.60324e-05}`.
Local slope: `tx(z) = bx + 2 cx dz + 3 cx dRatio dz^2`, `ty = by`.
Parameters: `(ax, bx, cx, ay, by)` = 5.

### Steps

1. **x-z fit** (`PrTrackFitterXZ.h`), on x-layer hits only, 3 parameters. Minimise
   `chi2_xz = sum_{i in X} w_i (u_i - x(z_i))^2`.
   Candidates are first built from hit combinations in T1/T3 plus a parabola search (Hough-like).
2. **Add stereo hits.** For each U/V layer predict `x_pred`, accept hits with `u_i` in a window
   `[x_pred - y_max*dxdy, x_pred - y_min*dxdy]`.
3. **y-z fit** (`PrTrackFitterYZ.h`), 2 parameters (`ay`, `by`). The stereo hit measures
   `u_i = x(z_i) + y(z_i) dxdy_l`, so with x(z) fixed from step 1:

       (u_i - x(z_i)) / dxdy_l = ay + by * dz_i ,          weight  w_i * dxdy_l^2
       chi2_yz = sum_{i in U,V} w_i ( u_i - x(z_i) - dxdy_l (ay + by dz_i) )^2

4. **Full XYZ fit** (`PrTrackFitterXYZ.h`), all 5 parameters on all N hits:

       chi2_5 = sum_i w_i ( u_i - x(z_i) - dxdy_l(i) * y(z_i) )^2 ,   dof = N - 5

   (iterated, removing the worst hit while chi2/dof or per-hit chi2 is too large).
5. Output a track with state at `z_ref`: `(x=ax, y=ay, tx=bx, ty=by, curvature from cx)`; momentum from
   `cx` via the momentum tool.

Information content: N hits give N measurements, N-5 degrees of freedom (e.g. N=12 -> 7).
**Time is not used anywhere.**

---

## 2. Time model shared by both proposals

Assume every hit has a corrected time `t_i` with resolution `sigma_t` (not confirmed to exist, see top).

### 2.1 Hit time

    t_i = t0 + L_i / (beta c) + tau_i + noise

- `t0`: collision (production) time at the track origin `(x0,y0,z0)`.
- `L_i`: path length from the origin to the hit. Straight-line approximation `L_i ~ (z_i - z0) * k`.
  (The bend in the magnet is neglected; a better version integrates the path using the momentum.)
- `tau_i`: signal propagation along the fibre to the SiPM, with `v_f` the signal speed in the fibre
  (about 5-6 ns/m, value to be confirmed):

      tau_i = (Y_ro - y_i) / v_f   for hits read out at +Y_ro  (sign flips for the other half)

  With `y_i = ay + by dz_i` this is **linear in ay, by**. It can be several ns, so it must be modelled.
  `Y_ro` is the y of the SiPM edge (readout side) and depends on the track half (up/down).

### 2.2 Linear time-vs-z form

Defining the "arrival-time line" with the origin dependence absorbed:

    t_i - tau_i = at + bt * dz_i                         (dz_i = z_i - z_ref)
    bt = k / (beta c) ,     at = t0 + (z_ref - z0) * bt

So **`at` is the time at z_ref**, not t0. The seed measures at, and t0 = at - (z_ref - z0) bt needs the
origin z0 (from Velo or PV). That degeneracy (t0 vs z0) is irreducible from SciFi alone: a delay `dt` is
equivalent to an origin shift `dz0 = c dt / k`. The PV z spread (~50 mm ~ 170 ps) is as large as the bunch
time spread, so `at` carries this smearing unless z0 is supplied.

Centring z on `z_ref` also decorrelates `at` and `bt` (hits are at z ~ 7.7-9.4 m, far from z=0, so without
centring they are almost perfectly anticorrelated).

### 2.3 Time chi2

    chi2_t = sum_i ( t_i - tau_i(ay,by) - at - bt dz_i )^2 / sigma_t,i^2

Slow particles: `1/beta = sqrt(1 + m^2/p^2)`, so `bt = k sqrt(1 + m^2/p^2)/c`. For 2 GeV/c protons
beta ~ 0.90, bt is ~11% larger than for beta = 1 (about 0.7 ns over the 1.8 m SciFi lever arm). With a
pion mass assumption, protons show up as time-residual outliers.

---

## 3. Scheme A: 6 parameters (bt fixed), sequential

Parameters `(ax, bx, cx, ay, by, at)`.

1. Run the original steps 1-4 unchanged to get `(ax,bx,cx,ay,by)`.
2. At each hit compute `tx_i = tx(z_i)`, `ty = by`, `k_i = sqrt(1+tx_i^2+ty^2)`, `y_i = y(z_i)`, `tau_i`,
   and the path length `L_i` (integrating `k` along z between layers is better than one global k).
3. Time residuals with the slope fixed to the light-speed (or momentum-based) value:

       r_i = t_i - tau_i - L_i/(beta c) ,  beta c = c  (pion-mass-based beta optional)

4. Fit one parameter by weighted mean:

       at_hat = sum_i r_i / sigma_t,i^2  /  sum_i 1/sigma_t,i^2 ,    sigma_at = ( sum_i 1/sigma_t,i^2 )^(-1/2)
       chi2_t = sum_i (r_i - at_hat)^2 / sigma_t,i^2 ,   dof_t = N - 1

5. Use `chi2_t`, and consistency of `t0 = at_hat - (z_ref - z0) bt` with the bunch crossing window /
   PV time, to reject ghosts and out-of-time hits.

Total counting: `2N` measurements (N positions + N times), 6 parameters, `dof = 2N - 6`.
Pros: spatial fit untouched, very stable, sharpest ghost test.
Cons: biased for slow particles, errors in `tx,ty,y` feed into the time test without being fitted.

---

## 4. Scheme B: 7 parameters, joint (x, y, t) vs z

Parameters `(ax, bx, cx, ay, by, at, bt)`. Treat t like a third coordinate vs z:

    x(z) = ax + dz ( bx + dz cx (1 + dRatio dz) )
    y(z) = ay + by dz
    t(z) = at + bt dz  +  tau(y(z))

Measurement vector per hit: `(u_i, t_i)`, with the model

    u_i : x(z_i) + dxdy_l(i) * y(z_i)
    t_i : at + bt dz_i + (s_i / v_f)(Y_ro - ay - by dz_i)      (s_i = +1/-1 for the readout half)

so `by` and `bt` mix in the time slope: the effective time slope is `bt - s_i by / v_f`.
In the joint fit that mixing is harmless because the stereo hits pin `y` much better than timing
(`sigma_y ~ 1 mm` versus ~ `v_f * sigma_t` ~ mm-cm). It matters only if the y fit is poor.

Combined chi2:

    chi2_7 = sum_i w_i ( u_i - x(z_i) - dxdy_l y(z_i) )^2
           + sum_i ( t_i - at - bt dz_i - tau_i(ay,by) )^2 / sigma_t,i^2
           + (bt - bt_prior)^2 / sigma_bt^2              <- optional Gaussian prior

with `bt_prior = k / c` (or `k sqrt(1+m^2/p^2)/c`) and a width `sigma_bt` for the beta spread:

- `sigma_bt -> 0` reproduces Scheme A (bt fixed).
- `sigma_bt -> infinity` gives the fully free 7-parameter fit.

`dof = 2N - 7` (or `2N - 6` effectively with a tight prior). The system is linear in all seven parameters
(except the weak `dRatio` dependence), so it can be solved with one normal-equation solve.

Pros: handles slow particles naturally; time can feed back to the spatial fit; symmetric treatment of x,y,t.
Cons: `at` and `bt` strongly correlated unless z is centred; `sigma_bt` large for short lever arms and few
layers (the lever arm is ~1.8 m = ~6 ns, so `sigma_bt/bt ~ sigma_t / 6 ns` per track before averaging);
more sensitive to the y-fit quality.

---

## 5. Comparison table

| | Original | A (6 par.) | B (7 par.) |
|---|---|---|---|
| Parameters | ax bx cx ay by | + at | + at, bt |
| Slope bt | - | fixed `k/c` (or momentum-based) | free, or prior |
| Measurements (N hits) | N | 2N | 2N |
| dof | N-5 | 2N-6 | 2N-7 |
| Fit structure | XZ, YZ, XYZ | original + 1-par. time | joint linear |
| Handles slow particles | n/a | no (unless beta hypothesis) | yes |
| Time lever arm needed | n/a | no | yes (weak) |
| Output extra | - | `at_hat`, `chi2_t` | `at`, `bt` (-> beta) |

## 6. Cautions (all schemes)

- Only `at` (time at `z_ref`) is measured; `t0` needs `z0`.
- Per-module/channel time offsets are indistinguishable from `at` and must be calibrated.
- `t(z)` is only approximately linear (path curvature in the magnet).
- Fewer than 12 layers (typically >= 9-10 hits) reduces dof and lever arm for both A and B.
- `sigma_t`, `v_f`, and the existence of a hit time field are unverified.

## 7. Proposed validation

Run original, A, B-with-prior, B-free on the Run 5 MC samples (`upgrade2_minbias_{1p0,1p3,1p5}e34_Jan2026`)
and compare efficiency, ghost rate, and the time residual width for pions vs protons, per pile-up.
