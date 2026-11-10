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

**Each hit i is one 1-D measurement** $u_i$ in layer $l(i)$ at known $z_i$: for X layer, $u_i = x_i$; 

$$u_i = x_i^0 + y_i \cdot \text{(dx/dy)}_l, \quad \text{(dx/dy)}_l =  \tan(\theta_l) & \text{(U,V layers)}, \quad \theta = \pm 5°$$

(`x_i^0` is the hit position at y=0, `dxdy` the layer slope; in the code `sciFiHits.x(i, y)` and `dxdy`.)
So a seed with N hits has N position measurements, not 3N. y enters only through stereo layers.

**Position uncertainty** (`PrStoreSciFiHits.cpp`, hard-coded, depends on cluster size `pseudoSize`=0..8):

$$\sigma_x \in \{0.05, 0.08, 0.11, 0.14, 0.17, 0.20, 0.23, 0.26, 0.29\} \text{ mm}, \quad w_i = 1/\sigma_x^2$$

For a stereo hit the information on y is $\sigma_y \sim \sigma_x / \tan(5°) \sim 11.4\, \sigma_x$.

**Reference z:** $z_{\text{ref}} = Z_{\text{MidT}} = 8520$ mm, $dz = z - z_{\text{ref}}$.

**Particle:** slopes $t_x = dx/dz$, $t_y = dy/dz$, $k = \sqrt{1 + t_x^2 + t_y^2}$, speed $\beta c$,
$c = 299.792$ mm/ns ($1/c = 3.3356$ ps/mm).

---

## 1. Original scheme: 5 parameters, space only (what the code does)

### Track model (`PrHybridSeedTrack.h`)

$$x(z) = a_x + dz \cdot ( b_x + dz \cdot c_x \cdot (1 + \text{dRatio} \cdot dz) ) \quad \text{(parabola + small cubic term)}$$
$$y(z) = a_y + b_y \cdot dz \quad \text{(straight line)}$$

`dRatio` is **not** a free parameter. It is a fixed constant (default $-0.000262$) in the x-z search and
parameterised in the final fit by `dRatioPar = {0.000267957, -8.651e-06, 4.60324e-05}`.
Local slope: $t_x(z) = b_x + 2 c_x dz + 3 c_x \text{dRatio} dz^2$, $t_y = b_y$.
Parameters: $(a_x, b_x, c_x, a_y, b_y)$ = 5.

### Steps

1. **x-z fit** (`PrTrackFitterXZ.h`), on x-layer hits only, 3 parameters. Minimise
   $$\chi^2_{xz} = \sum_{i \in X} w_i (u_i - x(z_i))^2$$
   Candidates are first built from hit combinations in T1/T3 plus a parabola search (Hough-like).
2. **Add stereo hits.** For each U/V layer predict $x_{\text{pred}}$, accept hits with $u_i$ in a window
   $[x_{\text{pred}} - y_{\max}\cdot\text{(dx/dy)}, x_{\text{pred}} - y_{\min}\cdot\text{(dx/dy)}]$.
3. **y-z fit** (`PrTrackFitterYZ.h`), 2 parameters ($a_y$, $b_y$). The stereo hit measures
   $u_i = x(z_i) + y(z_i) \text{(dx/dy)}_l$, so with $x(z)$ fixed from step 1:

$$\frac{u_i - x(z_i)}{\text{(dx/dy)}_l} = a_y + b_y \cdot dz_i, \quad \text{weight} \quad w_i \cdot \text{(dx/dy)}_l^2$$
$$\chi^2_{yz} = \sum_{i \in U,V} w_i \left( u_i - x(z_i) - \text{(dx/dy)}_l (a_y + b_y dz_i) \right)^2$$

4. **Full XYZ fit** (`PrTrackFitterXYZ.h`), all 5 parameters on all $N$ hits:

$$\chi^2_5 = \sum_i w_i \left( u_i - x(z_i) - \text{(dx/dy)}_l(i) \cdot y(z_i) \right)^2, \quad \text{dof} = N - 5$$

   (iterated, removing the worst hit while chi2/dof or per-hit chi2 is too large).
5. Output a track with state at $z_{\text{ref}}$: $(x=a_x, y=a_y, t_x=b_x, t_y=b_y, \text{curvature from } c_x)$; momentum from
   $c_x$ via the momentum tool.

Information content: $N$ hits give $N$ measurements, $N-5$ degrees of freedom (e.g. $N=12 \to 7$).
**Time is not used anywhere.**

---

## 2. Time model shared by both proposals

Assume every hit has a corrected time $t_i$ with resolution $\sigma_t$ (not confirmed to exist, see top).

### 2.1 Hit time

$$t_i = t_0 + \frac{L_i}{\beta c} + \tau_i + \text{noise}$$

- $t_0$: collision (production) time at the track origin $(x_0,y_0,z_0)$.
- $L_i$: path length from the origin to the hit. Straight-line approximation $L_i \sim (z_i - z_0) k$.
  (The bend in the magnet is neglected; a better version integrates the path using the momentum.)
- $\tau_i$: signal propagation along the fibre to the SiPM, with $v_f$ the signal speed in the fibre
  (about 5-6 ns/m, value to be confirmed):

$$\tau_i = \frac{Y_{\text{ro}} - y_i}{v_f} \quad \text{for hits read out at } +Y_{\text{ro}} \quad \text{(sign flips for the other half)}$$

  With $y_i = a_y + b_y dz_i$ this is **linear in $a_y, b_y$**. It can be several ns, so it must be modelled.
  $Y_{\text{ro}}$ is the y of the SiPM edge (readout side) and depends on the track half (up/down).

### 2.2 Linear time-vs-z form

Defining the "arrival-time line" with the origin dependence absorbed:

$$t_i - \tau_i = a_t + b_t \cdot dz_i, \quad dz_i = z_i - z_{\text{ref}}$$
$$b_t = \frac{k}{\beta c}, \quad a_t = t_0 + (z_{\text{ref}} - z_0) \cdot b_t$$

So **$a_t$ is the time at $z_{\text{ref}}$**, not $t_0$. The seed measures $a_t$, and $t_0 = a_t - (z_{\text{ref}} - z_0) b_t$ needs the
origin $z_0$ (from Velo or PV). That degeneracy ($t_0$ vs $z_0$) is irreducible from SciFi alone: a delay $dt$ is
equivalent to an origin shift $dz_0 = c \, dt / k$. The PV z spread (~50 mm ~ 170 ps) is as large as the bunch
time spread, so $a_t$ carries this smearing unless $z_0$ is supplied.

Centring $z$ on $z_{\text{ref}}$ also decorrelates $a_t$ and $b_t$ (hits are at $z \sim 7.7$-$9.4$ m, far from $z=0$, so without
centring they are almost perfectly anticorrelated).

### 2.3 Time chi2

$$\chi^2_t = \sum_i \frac{\left( t_i - \tau_i(a_y,b_y) - a_t - b_t dz_i \right)^2}{\sigma_{t,i}^2}$$

Slow particles: $1/\beta = \sqrt{1 + m^2/p^2}$, so $b_t = k \sqrt{1 + m^2/p^2}/c$. For 2 GeV/$c$ protons
$\beta \sim 0.90$, $b_t$ is $\sim$11% larger than for $\beta = 1$ (about 0.7 ns over the 1.8 m SciFi lever arm). With a
pion mass assumption, protons show up as time-residual outliers.

---

## 3. Scheme A: 6 parameters ($b_t$ fixed), sequential

Parameters $(a_x, b_x, c_x, a_y, b_y, a_t)$.

### Track model (space + time)

$$x(z) = a_x + dz \left( b_x + dz c_x (1 + \text{dRatio} \, dz) \right)$$
$$y(z) = a_y + b_y dz$$
$$t(z) = a_t + \frac{S(z)}{\beta c} + \tau\left( y(z) \right)$$

with the path-length term (arc length along the track from $z_{\text{ref}}$, $S(z_{\text{ref}})=0$):

$$S(z) = \int_{z_{\text{ref}}}^{z} \sqrt{1 + t_x(z')^2 + b_y^2} \, dz', \quad t_x(z') = b_x + 2 c_x dz' + 3 c_x \text{dRatio} \, dz'^2$$

and the fibre delay $\tau(y) = s (Y_{\text{ro}} - y)/v_f$ ($s = \pm 1$ for the readout side).
To first order ($t_x$ roughly constant over the SciFi) this is the straight line of section 2.2:

$$t(z) = a_t + b_t \cdot dz + \tau\left( y(z) \right), \quad b_t = \frac{k_{\text{ref}}}{\beta c}, \quad k_{\text{ref}} = \sqrt{1 + b_x^2 + b_y^2}$$

The key difference from scheme B: **$b_t$ is not a parameter**. It is a *derived* quantity, a function of
the already-fitted $b_x, c_x, b_y$ and a fixed $\beta$ (default 1, or $\sqrt{1+m^2/p^2}$ from the momentum implied
by $c_x$ and a mass hypothesis). Only the offset $a_t$ is free, so the time part has one parameter.
$a_t$ is the time at $z_{\text{ref}}$; the origin time is $t_0 = a_t - (z_{\text{ref}} - z_0) b_t$ once $z_0$ is known.

### Steps

1. Run the original steps 1-4 unchanged to get $(a_x,b_x,c_x,a_y,b_y)$.
2. At each hit compute $t_{x,i} = t_x(z_i)$, $t_y = b_y$, $k_i = \sqrt{1+t_{x,i}^2+t_y^2}$, $y_i = y(z_i)$, $\tau_i$,
   and the path length $S(z_i)$ (integrating $k$ along $z$ between layers is better than one global $k$).
3. Time residuals with the slope fixed to the light-speed (or momentum-based) value, i.e. data minus the
   $t(z)$ model above evaluated at $a_t = 0$:

$$r_i = t_i - \tau_i - \frac{S(z_i)}{\beta c}, \quad \beta = 1 \quad \text{(or from } p \text{ and a mass hypothesis)}$$

4. Fit one parameter by weighted mean:

$$\hat{a}_t = \frac{\sum_i r_i / \sigma_{t,i}^2}{\sum_i 1/\sigma_{t,i}^2}, \quad \sigma_{a_t} = \left( \sum_i \frac{1}{\sigma_{t,i}^2} \right)^{-1/2}$$
$$\chi^2_t = \sum_i \frac{(r_i - \hat{a}_t)^2}{\sigma_{t,i}^2}, \quad \text{dof}_t = N - 1$$

5. Use $\chi^2_t$, and consistency of $t_0 = \hat{a}_t - (z_{\text{ref}} - z_0) b_t$ with the bunch crossing window /
   PV time, to reject ghosts and out-of-time hits.

Total counting: $2N$ measurements ($N$ positions $+ N$ times), 6 parameters, $\text{dof} = 2N - 6$.
Pros: spatial fit untouched, very stable, sharpest ghost test.
Cons: biased for slow particles, errors in $t_x,t_y,y$ feed into the time test without being fitted.

---

## 4. Scheme B: 7 parameters, joint (x, y, t) vs z

Parameters $(a_x, b_x, c_x, a_y, b_y, a_t, b_t)$. Treat $t$ like a third coordinate vs $z$:

$$x(z) = a_x + dz \left( b_x + dz c_x (1 + \text{dRatio} \, dz) \right)$$
$$y(z) = a_y + b_y dz$$
$$t(z) = a_t + b_t dz + \tau\left(y(z)\right)$$

Measurement vector per hit: $(u_i, t_i)$, with the model

$$u_i : x(z_i) + \text{(dx/dy)}_l(i) \cdot y(z_i)$$
$$t_i : a_t + b_t dz_i + \frac{s_i}{v_f}\left(Y_{\text{ro}} - a_y - b_y dz_i\right) \quad (s_i = \pm 1 \text{ for the readout half})$$

so $b_y$ and $b_t$ mix in the time slope: the effective time slope is $b_t - s_i b_y / v_f$.
In the joint fit that mixing is harmless because the stereo hits pin $y$ much better than timing
($\sigma_y \sim 1$ mm versus $\sim v_f \sigma_t$ ~ mm-cm). It matters only if the y fit is poor.

Combined chi2:

$$\chi^2_7 = \sum_i w_i \left( u_i - x(z_i) - \text{(dx/dy)}_l y(z_i) \right)^2 + \sum_i \frac{\left( t_i - a_t - b_t dz_i - \tau_i(a_y,b_y) \right)^2}{\sigma_{t,i}^2} + \frac{(b_t - b_{t,\text{prior}})^2}{\sigma_{b_t}^2}$$

(Optional Gaussian prior on $b_t$.)

with $b_{t,\text{prior}} = k / c$ (or $k\sqrt{1+m^2/p^2}/c$) and a width $\sigma_{b_t}$ for the beta spread:

- $\sigma_{b_t} \to 0$ reproduces Scheme A ($b_t$ fixed).
- $\sigma_{b_t} \to \infty$ gives the fully free 7-parameter fit.

$\text{dof} = 2N - 7$ (or $2N - 6$ effectively with a tight prior). The system is linear in all seven parameters
(except the weak `dRatio` dependence), so it can be solved with one normal-equation solve.

Pros: handles slow particles naturally; time can feed back to the spatial fit; symmetric treatment of x,y,t.
Cons: $a_t$ and $b_t$ strongly correlated unless z is centred; $\sigma_{b_t}$ large for short lever arms and few
layers (the lever arm is ~1.8 m = ~6 ns, so $\sigma_{b_t}/b_t \sim \sigma_t / 6\,\text{ns}$ per track before averaging);
more sensitive to the y-fit quality.

---

## 5. Comparison table

| | Original | A (6 par.) | B (7 par.) |
|---|---|---|---|
| Parameters | $a_x b_x c_x a_y b_y$ | $+ a_t$ | $+ a_t, b_t$ |
| Slope $b_t$ | — | fixed $k/c$ (or momentum-based) | free, or prior |
| Measurements ($N$ hits) | $N$ | $2N$ | $2N$ |
| dof | $N-5$ | $2N-6$ | $2N-7$ |
| Fit structure | XZ, YZ, XYZ | original + 1-par. time | joint linear |
| Handles slow particles | n/a | no (unless beta hypothesis) | yes |
| Time lever arm needed | n/a | no | yes (weak) |
| Output extra | — | $\hat{a}_t$, $\chi^2_t$ | $a_t$, $b_t$ (→ $\beta$) |

## 6. Cautions (all schemes)

- Only $a_t$ (time at $z_{\text{ref}}$) is measured; $t_0$ needs $z_0$.
- Per-module/channel time offsets are indistinguishable from $a_t$ and must be calibrated.
- $t(z)$ is only approximately linear (path curvature in the magnet).
- Fewer than 12 layers (typically $\geq 9$-$10$ hits) reduces dof and lever arm for both A and B.
- $\sigma_t$, $v_f$, and the existence of a hit time field are unverified.

## 7. Proposed validation

Run original, A, B-with-prior, B-free on the Run 5 MC samples (`upgrade2_minbias_{1p0,1p3,1p5}e34_Jan2026`)
and compare efficiency, ghost rate, and the time residual width for pions vs protons, per pile-up. Fit parameters and residuals can be extracted directly into histograms for validation against the model.
