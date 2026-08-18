# Formula reading guide

This companion gives a plain-English reading of every substantive mathematical
display in the [article PDF](../paper/group_contaminated_structured_outcomes.pdf).
It is separate from the journal manuscript so that
the article retains conventional mathematical style. The readings explain what
the symbols assert; the hypotheses and proofs in the paper determine when the
assertions are valid.

## 1. Observation model and measurable group action

### Recorded versus intrinsic outcome

\[
X=\Gamma\cdot Y(A).
\]

**Reading.** The recorded structured outcome \(X\) is the intrinsic potential
outcome under the treatment actually received, \(Y(A)\), transformed by an
unobserved acquisition element \(\Gamma\). The dot denotes the specified group
action, not scalar multiplication. The model does not require \(\Gamma\) to be
independent of treatment, covariates, or the intrinsic outcome.

### Group-action laws

\[
(g,y)\longmapsto g\cdot y,\qquad
e\cdot y=y,\qquad
g\cdot(h\cdot y)=(gh)\cdot y .
\]

**Reading.** A group element \(g\) transforms an outcome \(y\). The identity
element \(e\) leaves every outcome unchanged. Applying \(h\) and then \(g\)
has the same result as applying their group product \(gh\). In the paper the
action map is also assumed jointly Borel measurable.

### Orbit and invariant target

\[
[y]_{\mathcal G}=\{g\cdot y:g\in\mathcal G\},
\qquad
\tau(g\cdot y)=\tau(y).
\]

**Reading.** The orbit of \(y\) is the set of every outcome obtainable from
\(y\) by an allowed nuisance transformation. A target \(\tau\) is invariant
when it has the same value at every point of each orbit.

## 2. Sharp quotient observability

### Uniform decoder

\[
D(g\cdot y)=\tau(y)
\quad
\text{for every }g\in\mathcal G\text{ and }y\in\mathcal Y .
\]

**Reading.** A single Borel decoder \(D\) must recover the intrinsic target
\(\tau(y)\) from every possible transformed version \(g\cdot y\), not merely
with high probability or on average.

### Necessary and sufficient condition

\[
\bigl[\exists D:\ D(g\cdot y)=\tau(y)\ \text{for all }g,y\bigr]
\quad\Longleftrightarrow\quad
\bigl[\tau(g\cdot y)=\tau(y)\ \text{for all }g,y\bigr].
\]

**Reading.** Exact recovery under unrestricted group contamination is possible
if and only if the target itself is constant on group orbits.

### Core equality in the converse proof

\[
\tau(g\cdot y)=D(g\cdot y)=\tau(y).
\]

**Reading.** The identity transformation first forces \(D(z)=\tau(z)\) at
every untransformed point \(z\). Applying this at \(z=g\cdot y\), and then
using the decoder property, proves that \(\tau\) must be invariant.

### Observationally indistinguishable noninvariant targets

\[
\begin{array}{lll}
\text{Model I:} & Y(a)=y,       & \Gamma=g,\\
\text{Model II:}& Y(a)=g\cdot y,& \Gamma=e .
\end{array}
\qquad\Longrightarrow\qquad
X=g\cdot y\ \text{in both models}.
\]

**Reading.** One model transforms the intrinsic value \(y\) by \(g\); the
other takes \(g\cdot y\) as intrinsic and applies the identity. Both produce
the same recorded observation. If
\(\tau(g\cdot y)\ne\tau(y)\), their intrinsic target values differ, proving
nonidentifiability of that noninvariant target.

## 3. Maximal invariants

### Definition

\[
M(y)=M(z)
\quad\Longleftrightarrow\quad
z=g\cdot y\ \text{for some }g\in\mathcal G .
\]

**Reading.** A maximal invariant assigns the same code exactly to outcomes in
the same orbit. It discards which representative of the orbit was recorded,
but it does not merge two distinct orbits.

### Factorization of every invariant target

\[
h=\bar h\circ M .
\]

**Reading.** Every Borel invariant target \(h\) can be evaluated by first
computing the maximal invariant \(M\) and then applying a Borel map
\(\bar h\). Thus \(M\) contains every Borel-measurable feature that survives
the nuisance action.

### Separation step in the Borel factorization proof

\[
M(A)\subseteq D_B,
\qquad
M(\mathcal Y\setminus A)\subseteq\mathcal S\setminus D_B,
\qquad
A=h^{-1}(B).
\]

**Reading.** For a Borel target event \(B\), the set \(A\) of outcomes mapped
into \(B\) is a union of complete orbits. The Lusin separation theorem supplies
a Borel set \(D_B\) in the maximal-invariant space that contains precisely the
codes arising from \(A\), as opposed to its complement, among attainable
maximal-invariant values in \(M(\mathcal Y)\). It may contain unattainable
points outside \(M(\mathcal Y)\). This establishes the
measurability needed for \(h=\bar h\circ M\).

### Orbit code for a compact action

\[
M_{\mathrm{orb}}(y)=\mathcal G\cdot y
=\{g\cdot y:g\in\mathcal G\}.
\]

**Reading.** For a compact metrizable group acting continuously on a Polish
outcome space, the complete compact orbit itself can be used as a maximal
invariant. Its codomain is the standard Borel hyperspace of nonempty compact
subsets.

### Vietoris preimages used to prove measurability

\[
\begin{aligned}
\{y:M_{\mathrm{orb}}(y)\cap U\ne\varnothing\}
  &=\bigcup_{g\in\mathcal G}g^{-1}U,\\
\{y:M_{\mathrm{orb}}(y)\subseteq U\}
  &=\mathcal Y\setminus
    \bigcup_{g\in\mathcal G}g^{-1}(\mathcal Y\setminus U).
\end{aligned}
\]

**Reading.** The first set contains outcomes whose orbit hits the open set
\(U\); equivalently, some group-transformed version lies in \(U\). The second
contains outcomes whose entire orbit lies in \(U\). These are the two kinds of
sets generating the Vietoris topology. Compactness and continuity make both
preimages open, which makes the orbit map Borel—in fact, continuous.

### Canonical maximal invariant for a finite group

\[
j^\star(y)
=
\min\arg\min_{1\le j\le m}\nu(h_j\cdot y),
\qquad
c_H(y)=h_{j^\star(y)}\cdot y .
\]

**Reading.** List the finite group as
\(H=\{h_1,\ldots,h_m\}\). Evaluate the injective Borel ordering code \(\nu\)
on every transformed point \(h_j\cdot y\), choose the smallest coded orbit
representative, and break a group-index tie by the smallest index. The
resulting \(c_H\) is Borel and maximal. Injectivity of \(\nu\) means that
different orbit points cannot tie, although stabilizers can make different
group indices produce the same point.

## 4. Quotient potential outcomes and causal identification

### Observability of the quotient outcome

\[
Q(a)=M\{Y(a)\},
\qquad
Q=M(X)
=M\{\Gamma\cdot Y(A)\}
=M\{Y(A)\}
=Q(A).
\]

**Reading.** The quotient potential outcome under treatment \(a\) is the
maximal-invariant code of the intrinsic potential outcome. Applying \(M\) to
the recorded outcome removes the unknown group element exactly, so the
observed quotient value is the quotient potential outcome under the treatment
received.

### Target-specific causal assumptions

\[
Q(a)\mathbin{\perp\!\!\!\perp}A\mid C,
\qquad
\mathbb P(A=a\mid C)>0
\quad\text{almost surely}.
\]

**Reading.** Conditional on measured pretreatment covariates \(C\), treatment
assignment is independent of the quotient potential outcome under treatment
\(a\). Positivity requires treatment \(a\) to have nonzero conditional
probability throughout the target covariate population. These assumptions are
about the quotient target; group invariance alone does not imply them.

### Full-law \(g\)-formula

\[
\mathbb P\{Q(a)\in B\}
=
\int
\mathbb P(Q\in B\mid A=a,C=c)\,dP_C(c).
\]

**Reading.** The interventional probability that the quotient outcome under
treatment \(a\) belongs to a Borel set \(B\) equals the factual probability
among units receiving \(a\), conditional on covariates \(c\), averaged over
the target covariate distribution. Because this equality holds for every
Borel \(B\), it identifies the complete probability law of \(Q(a)\), not only
its mean.

### Three steps in the identification proof

\[
\begin{aligned}
\mathbb P\{Q(a)\in B\}
&=\int\mathbb P\{Q(a)\in B\mid C=c\}\,dP_C(c)\\
&=\int\mathbb P\{Q(a)\in B\mid A=a,C=c\}\,dP_C(c)\\
&=\int\mathbb P(Q\in B\mid A=a,C=c)\,dP_C(c).
\end{aligned}
\]

**Reading.** The first line is iterated expectation. The second uses
conditional exchangeability, with positivity ensuring that the treatment-\(a\)
conditional law is defined on the relevant covariate support. The third uses
quotient consistency, \(Q=Q(A)\).

## 5. Lattice rigid-motion quotient

### Bounded-support image class

\[
x:\mathbb Z^2\longrightarrow\{0,\ldots,255\}^{q},
\qquad x\in\mathcal X_{q,L}.
\]

**Reading.** A \(q\)-channel image assigns a \(q\)-vector of 8-bit intensities
to every lattice location. The nonzero support has a bounding box no larger
than \(L\) rows by \(L\) columns; the all-zero image is included separately.
The lattice is unbounded even though each image has bounded finite support.

### Semidirect-product multiplication

\[
(t,r)(u,s)
=
\bigl(t+R_r u,\ r+s\bmod 4\bigr).
\]

**Reading.** A rigid motion consists of an integer translation
\(t\in\mathbb Z^2\) and a quarter-turn index \(r\in C_4\). When composing
\((u,s)\) followed by \((t,r)\), the earlier translation \(u\) must first be
rotated by \(R_r\); translations then add, and quarter-turn indices add modulo
four. This noncommutative multiplication defines
\(\mathbb Z^2\rtimes C_4\).

### Action on an image

\[
\{(t,r)\cdot x\}(v)
=
x\{R_r^{-1}(v-t)\},
\qquad v\in\mathbb Z^2.
\]

**Reading.** To determine the transformed pixel at location \(v\), first undo
the translation \(t\), then undo the quarter turn \(R_r\), and read the
original image at that preimage location. This is the standard pullback action
of a lattice rigid motion.

### Support-bounding-box origin

\[
b(x)=
\left(
\min_{v\in\operatorname{supp}(x)}v_1,\,
\min_{v\in\operatorname{supp}(x)}v_2
\right).
\]

**Reading.** For a nonzero image, \(b(x)\) is the componentwise lower corner
of its nonzero support bounding box: the smallest occupied first coordinate
and the smallest occupied second coordinate.

### Translation normalization

\[
N(x)=(-b(x),0)\cdot x,
\qquad
N(0)=0.
\]

**Reading.** Translate a nonzero image so that the lower corner of its support
bounding box is at the lattice origin, without rotating it. The zero image is
defined to normalize to itself.

### Shape-aware serialization key

\[
\kappa\{N(x)\}
=
\bigl(h(x),w(x),\operatorname{bytes}\{N(x)\}\bigr).
\]

**Reading.** The canonicalization key first records the normalized support
height and width as integers, then the channel bytes in fixed order. Keys are
compared lexicographically. Recording dimensions prevents nonsquare rotated
arrays with the same byte sequence from being treated as the same shaped
array.

### Four normalized rotation candidates

\[
x_r=N\{(0,r)\cdot x\},
\qquad r\in C_4.
\]

**Reading.** Rotate the image by each of the four quarter turns and then remove
translation from that rotated image. The four \(x_r\)'s are the candidate
representatives of the lattice rigid-motion orbit.

### Canonical representative

\[
c(x)=x_{r^\star},
\qquad
r^\star
=
\min\arg\min_{r\in C_4}\kappa(x_r).
\]

**Reading.** Serialize each candidate with its bounding-box dimensions and
channel bytes. Choose the lexicographically smallest serialization. If more
than one group index produces the same minimizing image because of symmetry,
choose the smallest index. For the zero image, \(c(0)=0\).

### Maximality of the lattice code

\[
c(x)=c(y)
\quad\Longleftrightarrow\quad
y=(t,r)\cdot x
\ \text{for some }(t,r)\in\mathbb Z^2\rtimes C_4.
\]

**Reading.** Two bounded-support lattice images have the same canonical code
exactly when one is an integer translation and quarter-turn rotation of the
other. Thus the code removes precisely the declared nuisance action.

### Translation-normalization identity

\[
N\{(t,0)\cdot z\}=N(z).
\]

**Reading.** Translating an image before moving its support bounding box to
the origin makes no difference: the normalization removes every integer
translation exactly.

### Candidate-set equality under a rigid motion

\[
N\{(0,r)\cdot y\}
=
N\{(R_rt,r+s)\cdot x\}
=
N\{(0,r+s)\cdot x\},
\qquad y=(t,s)\cdot x.
\]

**Reading.** If \(y\) is a translated and rotated copy of \(x\), rotating
\(y\) by \(r\) produces a translated version of \(x\) rotated by \(r+s\).
Normalization removes the remaining translation. As \(r\) ranges over all
four values, \(r+s\) does too, so \(x\) and \(y\) have the same four
canonicalization candidates.

### Common representative in the converse proof

\[
z=(u,r)\cdot x=(v,s)\cdot y,
\qquad
y=(v,s)^{-1}(u,r)\cdot x.
\]

**Reading.** If the canonical codes of \(x\) and \(y\) agree, their common
canonical image \(z\) is a rigid-motion transform of each. Undoing the
transformation from \(y\) to \(z\) expresses \(y\) as a rigid-motion transform
of \(x\), proving that they lie in the same orbit.

### Two-site well code

\[
\mathcal G_{\mathrm{well}}
=
\mathcal G_{\mathrm{rig}}\times\mathcal G_{\mathrm{rig}},
\qquad
C(x_1,x_2)=\bigl(c(x_1),c(x_2)\bigr).
\]

**Reading.** Each of the two labeled sites can undergo its own lattice rigid
motion. The well-level maximal invariant is the ordered pair of its two
site-specific canonical images. The order is retained; the construction does
not permute site labels.

## 6. Invariant kernel

### Fixed-dimensional canonical embedding

\[
\psi\{C(w)\}\in\mathbb R^{2qL_0^2},
\qquad L_0\ge L.
\]

**Reading.** Place each of the two canonical support crops at the upper-left
of an \(L_0\)-by-\(L_0\) zero canvas and concatenate all \(q\) channels and
both sites. The map has \(2qL_0^2\) coordinates. Because each crop is its
minimal nonzero support box, this Borel storage map is injective on canonical
representatives.

### Gaussian quotient kernel

\[
k_\sigma(w,w')
=
\exp\left[
-\frac{
\|\psi\{C(w)\}-\psi\{C(w')\}\|_2^2
}{2\sigma^2}
\right],
\qquad \sigma>0.
\]

**Reading.** Compute the squared Euclidean distance between the two canonical
well vectors, divide by twice the squared bandwidth, negate it, and
exponentiate. Identical quotient codes have similarity one; more distant
codes have similarity closer to zero.

### Positive-definiteness calculation

\[
\sum_{i,j=1}^n a_i a_j k_\sigma(w_i,w_j)
=
\sum_{i,j=1}^n a_i a_j
k_{\mathrm{Gauss}}\!\left(\psi C(w_i),\psi C(w_j)\right)
\ge 0.
\]

**Reading.** For every finite set of wells and real coefficients, the kernel
quadratic form is nonnegative because it is exactly the Gaussian-kernel
quadratic form after canonical embedding. This proves positive definiteness.
The Gaussian kernel is characteristic, and the Borel injectivity of \(\psi\)
then makes the quotient kernel distinguish probability laws of the maximal
invariant.

## 7. Finite directional Euler signature

### Cubical Euler characteristic

\[
\chi(K)=n_0(K)-n_1(K)+n_2(K).
\]

**Reading.** For a planar cubical complex \(K\), its Euler characteristic is
the number of vertices minus the number of edges plus the number of square
faces.

The implementation first applies Otsu thresholding to the canonical nuclear
channel and removes 8-connected foreground components with fewer than four
pixels.

### Shape-adaptive centered lattice coordinate

\[
\rho_{h,w}(u_1,u_2)
=
\bigl(2u_1-(w-1),\,2u_2-(h-1)\bigr).
\]

**Reading.** For a canonical mask of width \(w\) and height \(h\), the
horizontal and vertical pixel indices are doubled and recentered so that the
bounding rectangle is symmetric about zero. This normalization is recomputed
for each canonical mask; it is not a common physical coordinate system across
different mask dimensions.

### Shape-adaptive Euler sweep levels

\[
t_{h,w,v,\ell}
=
m_{h,w,v}
+\frac{\ell}{J-1}(M_{h,w,v}-m_{h,w,v}),
\qquad
\ell=0,\ldots,J-1.
\]

**Reading.** For direction \(v\), \(m_{h,w,v}\) and \(M_{h,w,v}\) are the
smallest and largest directional heights over the mask's full bounding
rectangle. The \(\ell\)-th cutoff divides that outcome-specific height range
into \(J-1\) equal intervals. The implementation fixes the distinct level-count
symbol \(J=25\); \(L\) elsewhere denotes the image-support bound.

### Secondary finite Euler vector

\[
F(w)=
\left(
\chi\{K_{j,v,\ell}(c(x_j))\}
\right)_{
j\in\{1,2\},\,
v\in V,\,
\ell\in\{0,\ldots,J-1\}
}.
\]

**Reading.** Canonicalize each site first. For each site \(j\), chosen
direction \(v\), and normalized filtration index \(\ell\), form the cubical
complex from retained pixels whose centered directional height does not exceed
the adaptive cutoff \(t_{h,w,v,\ell}\), and record its Euler characteristic.
The implemented vector uses eight directions and 25 levels per direction for
each site.

\[
F(g\cdot w)=F(w).
\]

**Reading.** The finite Euler vector is exactly invariant because it is
computed after the maximal-invariant canonicalization. This equality does not
make the finite vector maximal or imply that it determines an arbitrary
outcome distribution.

## 8. Paired kernel statistic

### Assignment vector and assignment space

\[
Z=(Z_1,\ldots,Z_B),
\qquad
\Omega=\{0,1\}^B.
\]

**Reading.** There are \(B\) paired blocks. The two wells are ordered
deterministically by a pretreatment identifier; \(Z_b\) is the treatment label assigned to the first well,
and the second receives \(1-Z_b\). The set
\(\Omega\) contains all \(2^B\) possible within-block swap assignments.
Uniformity on \(\Omega\) is an explicit design assumption. In RxRx1, same-plate
metadata verify eligibility for a paired swap, not uniformity of the original
randomization algorithm. The theorem assumes uniformity conditional on the
eligible wells, their complete potential-outcome schedule, and pretreatment
design information; equivalently, paired assignment is randomized
independently of those potential outcomes within the stated design.

### Treatment-indexed samples induced by an assignment

\[
\mathcal Q_1(z)=\{q_{b,1-z_b}:1\le b\le B\},
\qquad
\mathcal Q_0(z)=\{q_{b,z_b}:1\le b\le B\}.
\]

**Reading.** Under a proposed assignment \(z\), condition 1 receives the second
ordered outcome when \(z_b=0\) and the first when \(z_b=1\); condition 0
receives the other outcome. This matches the implementation, which assigns
labels \((z_b,1-z_b)\) to the ordered pair. Label swapping changes group
membership, not the observed outcome values.

### Population maximum mean discrepancy

\[
\operatorname{MMD}_k^2(P,P')
=
\mathbb E\,k(U,U')
+\mathbb E\,k(V,V')
-2\mathbb E\,k(U,V),
\]

where \(U,U'\) are independent draws from \(P\), and \(V,V'\) are independent
draws from \(P'\).

**Reading.** Squared MMD is average similarity within the first law plus
average similarity within the second law minus twice the average similarity
between the laws. For the characteristic quotient kernel, it is zero exactly
when the two quotient laws are equal.

### Empirical paired-block discrepancy statistic

\[
\begin{aligned}
\widehat{\operatorname{MMD}}_u^2(z)
={}&
\frac{1}{B(B-1)}
\sum_{\substack{b,b'=1\\b\ne b'}}^B
k(q_{b,1-z_b},q_{b',1-z_{b'}})\\
&+
\frac{1}{B(B-1)}
\sum_{\substack{b,b'=1\\b\ne b'}}^B
k(q_{b,z_b},q_{b',z_{b'}})\\
&-
\frac{2}{B^2}
\sum_{b,b'=1}^B
k(q_{b,z_b},q_{b',1-z_{b'}}).
\end{aligned}
\]

**Reading.** The first term averages kernel similarity between distinct blocks
within condition 1. The second does the same within condition 0. The third
subtracts twice the average similarity across conditions, including
same-block cross-condition pairs. Under independent identically distributed
samples this conventional formula is unbiased for population squared MMD.
With matched blocks, within-pair dependence can remove that unbiasedness; in
the paper it is used as a prespecified randomization statistic, whose exact
test validity does not require unbiased superpopulation estimation.

### Label-invariant bandwidth

\[
\widehat\sigma^2
=
\frac12\operatorname{median}
\left\{
\|z_i-z_j\|_2^2:
i<j,\ \|z_i-z_j\|_2^2>0
\right\},
\qquad z_i=\psi\{C(w_i)\}.
\]

**Reading.** Square every positive Euclidean distance between the pooled
canonical vectors from the contrast being tested, take their median, and
divide it by two to obtain the
squared Gaussian bandwidth. Equivalently, the bandwidth is the square root of
half that median squared distance. If there is no positive pairwise distance,
the implementation uses \(\widehat\sigma=1\). Because treatment labels do not
enter this calculation, the bandwidth stays fixed throughout the
randomization distribution.

## 9. Fisher exact randomization test

### Exact upper-tail \(p\)-value

\[
p(Z)
=
2^{-B}
\sum_{z\in\Omega}
\mathbf 1\{T(z)\ge T(Z)\}.
\]

**Reading.** Enumerate every one of the \(2^B\) within-block assignments.
The exact \(p\)-value is the fraction whose statistic is at least as large as
the statistic under the observed assignment. Ties are included in the upper
tail.

### Conservative floating-point comparison

\[
T(z)\ge T(Z)-10^{-12}.
\]

**Reading.** The software treats statistics within \(10^{-12}\) below the
observed statistic as upper-tail ties. This can only increase the computed
\(p\)-value relative to the exact mathematical comparison.

### Fisher sharp null

\[
H_0^{\mathrm{sharp}}:
\quad
Q_{bj}(1)=Q_{bj}(0)
\quad
\text{for every }b\in\{1,\ldots,B\},\ j\in\{0,1\}.
\]

**Reading.** For each of the two eligible wells in every block, changing
between the two selected treatment conditions would leave that well's
maximal-invariant potential outcome unchanged. This unit-level sharp null is
stronger than equality of two marginal population distributions.

### Finite-sample conditional validity

\[
\mathbb P\!\left\{
p(Z)\le\alpha
\ \middle|\
\text{eligible wells, potential outcomes, and design information}
\right\}
\le\alpha .
\]

**Reading.** Conditional on the eligible experimental units, all their
potential outcomes, and the pretreatment design information, the probability
of rejecting with an exact \(p\)-value at most \(\alpha\) is no greater than
\(\alpha\), provided the assignment vector is uniform on \(\Omega\). The claim
is finite-sample and conditional; same-plate metadata alone do not prove the
uniform-assignment premise.

### Upper-tail rank

\[
r(z)=\#\{s\in\Omega:T(s)\ge T(z)\},
\qquad
p(z)=\frac{r(z)}{N},
\qquad
N=|\Omega|=2^B.
\]

**Reading.** The upper-tail rank \(r(z)\) counts how many assignments have a
statistic at least as large as assignment \(z\). Dividing by the total number
of assignments gives its exact \(p\)-value.

### Counting bound in the validity proof

\[
\#\{z:p(z)\le\alpha\}
\le
\lfloor\alpha N\rfloor
\le
\alpha N.
\]

**Reading.** At most \(\lfloor\alpha N\rfloor\) assignments can occupy the
most extreme \(\alpha\)-fraction of the randomization distribution. Ties only
make upper-tail ranks larger, so they cannot violate this bound. Uniform
assignment then gives conditional type-I error at most \(\alpha\).

### Eight confirmation blocks

\[
|\Omega|=2^8=256.
\]

**Reading.** Each RxRx1 contrast has eight independently swappable confirmation
blocks under the stated assignment premise, yielding 256 assignments in the
complete paired randomization distribution.

## 10. Discovery-only pair selection

### Robust within-batch normalization

\[
\widehat s_{er}
=
\begin{cases}
1.4826\operatorname{median}_{i\in\mathcal T_e}
\lvert W_{ier}-\operatorname{median}_{i'\in\mathcal T_e}W_{i'er}\rvert,
&\text{if this value is at least }10^{-6},\\
1,&\text{otherwise},
\end{cases}
\]
\[
E_{ier}
=
\frac{W_{ier}-\operatorname{median}_{i'\in\mathcal T_e}W_{i'er}}
{\widehat s_{er}} .
\]

**Reading.** For discovery batch \(e\) and embedding coordinate \(r\),
\(\mathcal T_e\) is the set of all noncontrol treatment wells in that batch.
The two site embeddings are first averaged within each well to give \(W_{ier}\).
Each coordinate is then centered by its within-batch treatment-well median and
scaled by 1.4826 times its median absolute deviation. A scale below
\(10^{-6}\) is replaced by one. No confirmation row enters this normalization.

### Split-half embedding summaries

\[
\begin{aligned}
\bar E_{jh}
&=
|H_h|^{-1}\sum_{e\in H_h}E_{je},
&
V_{jh}
&=
|H_h|^{-1}\sum_{e\in H_h}
\|E_{je}-\bar E_{jh}\|_2^2,\\
\delta_h(j,k)
&=
\bar E_{jh}-\bar E_{kh},
&
R_h(j,k)
&=
\frac{\|\delta_h(j,k)\|_2^2}
{V_{jh}+V_{kh}+10^{-12}}.
\end{aligned}
\]

**Reading.** For siRNA condition \(j\) and discovery half \(h\),
\(\bar E_{jh}\) is the average normalized 128-dimensional well embedding.
\(V_{jh}\) is its average squared residual norm across experiments in that
half. For candidate conditions \(j\) and \(k\), \(\delta_h(j,k)\) is their
centroid difference, and \(R_h(j,k)\) is the squared separation divided by the
sum of their within-condition variation. The \(10^{-12}\) constant prevents
division by zero.

### Split-half stability score

\[
S(j,k)
=
\min_{h\in\{1,2\}}R_h(j,k)
\max\left\{
\frac{
\langle\delta_1(j,k),\delta_2(j,k)\rangle
}{
\sqrt{
(\|\delta_1(j,k)\|_2^2+10^{-12})
(\|\delta_2(j,k)\|_2^2+10^{-12})
}
},
0
\right\}.
\]

**Reading.** The first factor is the weaker of the two half-specific
signal-to-noise ratios, so a candidate cannot score highly by separating in
only one discovery half. The second factor is the nonnegative part of the
cosine agreement between the two half-specific effect directions. Opposite
directions receive zero score. Candidate pairs must also satisfy the same-plate
and completeness gates in every discovery batch. Confirmation completeness and
same-plate occurrence are audited only after the discovery-only condition list
has been frozen.

## 11. Estimator-unobserved acquisition generator

### Coordinate-free morphology score

\[
m_{ws}
=
\operatorname{mean}(I_{ws}/255)
+0.25\,\operatorname{sd}(I_{ws}/255),
\qquad
\widetilde m
=
\operatorname{median}_{w,s}m_{ws}.
\]

**Reading.** Divide the six-channel 8-bit site array \(I_{ws}\) by 255. The
site score is its overall mean intensity plus one quarter of its population
standard deviation. The pooled median is the median score over all wells and
both sites. Both quantities are unchanged by pixel translations and quarter
turns.

### Treatment- and outcome-dependent group element

\[
\begin{aligned}
b_{ws}&=\mathbf 1\{m_{ws}>\widetilde m\},&
q_{ws}&=\left\lfloor 1000003\,|m_{ws}|\right\rfloor,\\
r_{ws}&=(H_{0,ws}\bmod 2+2a_w+b_{ws})\bmod4,&
d_w&=2a_w-1,\\
\Delta y_{ws}
&=d_w\{1+(H_{1,ws}+q_{ws})\bmod8\},&
\Delta x_{ws}
&=d_w\{1+(H_{2,ws}+7q_{ws}+b_{ws})\bmod8\}.
\end{aligned}
\]

**Reading.** The indicator \(b_{ws}\) records whether the realized morphology
score is above the pooled median, and \(q_{ws}\) is a deterministic integer
quantization of that score. The three \(H\)-values are the consecutive
little-endian unsigned 64-bit words from the 24-byte BLAKE2b digest of the
UTF-8 string `seed|well_id|site=s`. The quarter-turn count \(r_{ws}\) depends on the digest, treatment,
and realized morphology. The sign \(d_w\) makes the two treatment labels shift
in opposite directions, while the magnitudes depend on the digest and
morphology and lie between one and eight pixels. The realized group elements
are recorded for auditing but are not inputs to the representations or tests.

## 12. Approximate-action stress endpoint

\[
\varepsilon_m(\delta)
=
\frac{\|Z_m^{(\delta)}-Z_m^{(0)}\|_F}
{\max\{\|Z_m^{(0)}\|_F,10^{-12}\}}.
\]

**Reading.** For representation method \(m\), \(Z_m^{(0)}\) is the complete
feature matrix obtained after support-centering the primary-pair arrays
contaminated with the prespecified primary acquisition seed \(20260731\).
\(Z_m^{(\delta)}\) is the feature matrix after applying the named
outside-action perturbation. The numerator is the Frobenius norm of their
difference, divided by the baseline Frobenius norm with a \(10^{-12}\) floor.
For every perturbation, the label-free median bandwidth is re-estimated from
that perturbation's pooled primary-pair features before recomputing the
statistic and complete paired-swap \(p\)-value.

## 13. Partial acquisition and boundary loss

### Combined transformation and observation map

\[
\Phi(g,y)=\Pi(g\cdot y).
\]

**Reading.** First transform the intrinsic outcome \(y\) by the nuisance
element \(g\), then apply the possibly lossy observation operator \(\Pi\), such
as a fixed field-of-view crop. The result is the recorded object
\(\Phi(g,y)\).

### Decoder under partial observation

\[
D\{\Pi(g\cdot y)\}=\tau(y)
\quad\text{for every }g\in\mathcal G\text{ and }y\in\mathcal Y.
\]

**Reading.** One Borel decoder must recover the intrinsic target from every
allowed transformed and partially observed version of every intrinsic
outcome.

### Sharp fiber condition

\[
\Pi(g\cdot y)=\Pi(h\cdot z)
\quad\Longrightarrow\quad
\tau(y)=\tau(z).
\]

**Reading.** Whenever two intrinsic outcomes can produce exactly the same
partial observation, possibly after different nuisance transformations, their
target values must agree. This condition is both necessary and sufficient for
an exact Borel decoder.

### Separation step for the partial-observation decoder

\[
\Phi(A)\subseteq E_B,
\qquad
\Phi\{(\mathcal G\times\mathcal Y)\setminus A\}
\subseteq\mathcal X\setminus E_B.
\]

**Reading.** The Lusin separation theorem supplies a Borel recorded-data event
\(E_B\) that separates observations whose intrinsic target falls in a chosen
Borel set \(B\) from observations whose target does not. Constancy on the
fibers of \(\Phi\) makes the two analytic images disjoint.

## 14. Continuous rotations and finite-group canonicalization

### Continuous-rotation orbit code

\[
M_{\mathrm{rot}}(y)
=\{R_\theta\cdot y:\theta\in[0,2\pi)\}.
\]

**Reading.** The maximal invariant for an abstract continuous rotation action
assigns to \(y\) the complete set of all its planar rotations. This is a
Borel, orbit-valued code because \(\operatorname{SO}(2)\) is compact; it is not
an explicit finite raster canonicalizer.

### Borel cells of the finite canonicalizer

\[
\{y:j^\star(y)=j\}
=
\bigcap_{k<j}\{y:f_j(y)<f_k(y)\}
\cap
\bigcap_{k>j}\{y:f_j(y)\le f_k(y)\}.
\]

**Reading.** Index \(j\) is selected exactly when its injected orbit value is
strictly smaller than every earlier-indexed value and no larger than every
later-indexed value. These are finite intersections of Borel comparisons, so
the deterministic minimizing index is Borel. Injectivity makes the minimizing
orbit point unique even when several group indices represent that point
because of a stabilizer.

## 15. Conditional effects of scalar invariant targets

### Invariant-functional CATE

\[
\tau_h(c)
:=
\mathbb E\!\left[h\{Q(1)\}-h\{Q(0)\}\mid C=c\right]
=
\mathbb E\{h(Q)\mid A=1,C=c\}
-
\mathbb E\{h(Q)\mid A=0,C=c\}.
\]

**Reading.** For a prespecified integrable scalar functional \(h\) of the
quotient outcome, the conditional causal mean contrast at covariate value
\(c\) equals the difference between the two observed conditional means. This
identity requires quotient consistency, conditional exchangeability, and
positivity.

### Arm-specific conditional mean identity

\[
\mathbb E[h\{Q(a)\}\mid C=c]
=\mathbb E\{h(Q)\mid A=a,C=c\}.
\]

**Reading.** Within a covariate stratum, the conditional mean of the scalar
quotient potential outcome under arm \(a\) equals the observed conditional
mean among units receiving arm \(a\). Subtracting this equality for arms one
and zero proves the preceding CATE formula.

## 16. Persistence stability for an invariant diagnostic kernel

### Invariant diagnostic vector

\[
u_\zeta(w)=\zeta\{C(w)\}.
\]

**Reading.** First map the well to its exact maximal-invariant canonical
representative \(C(w)\), then apply the chosen Borel diagnostic map \(\zeta\).
In the experiment, this is the 16-by-16 resampled canonical nuclear-channel
array. It is a separate invariant diagnostic vector, not the full canonical
pixel vector used by the primary MMD test.

### Diagnostic Gaussian kernel and feature distance

\[
k_{\zeta,\sigma}(w,w')
=\exp\!\left[-\frac{\|u_\zeta(w)-u_\zeta(w')\|_2^2}{2\sigma^2}\right],
\qquad
d_{\zeta,\sigma}(w,w')
=\left[2-2k_{\zeta,\sigma}(w,w')\right]^{1/2}.
\]

**Reading.** The diagnostic Gaussian similarity is the exponential of minus
the squared Euclidean distance between invariant diagnostic vectors divided by
twice the squared bandwidth. The associated feature distance is the square
root of two minus twice that similarity.

### Exact diagram invariance

\[
\operatorname{Dgm}_{\zeta,p}(g\cdot w)
=\operatorname{Dgm}_{\zeta,p}(w).
\]

**Reading.** Applying any declared well-level lattice rigid motion before
canonicalization leaves the degree-\(p\) persistence diagram of the invariant
diagnostic representation exactly unchanged.

### Bottleneck bound in diagnostic-kernel geometry

\[
d_B\!\left\{
\operatorname{Dgm}_{\zeta,p}(w),
\operatorname{Dgm}_{\zeta,p}(w')
\right\}
\le
\sigma
\sqrt{-2\log\!\left(
1-\frac{d_{\zeta,\sigma}(w,w')^2}{2}
\right)}.
\]

**Reading.** The bottleneck distance between the two diagnostic persistence
diagrams is no larger than the Euclidean distance between their invariant
diagnostic vectors, written exactly as the displayed inverse-Gaussian function
of their diagnostic-kernel feature distance. This does not refer to the
primary full-image kernel and does not assert stability of fixed-threshold
Betti numbers.

### Standard persistence-stability chain

\[
d_B\{\operatorname{Dgm}_{\zeta,p}(w),
      \operatorname{Dgm}_{\zeta,p}(w')\}
\le \|f_{\zeta,w}-f_{\zeta,w'}\|_\infty
=\|u_\zeta(w)-u_\zeta(w')\|_\infty
\le\|u_\zeta(w)-u_\zeta(w')\|_2.
\]

**Reading.** Persistence stability bounds diagram distance by the largest
change in the lower-star function. Because the function is linearly extended
from its vertex values, that change equals the sup-norm difference between
diagnostic vectors, which is no greater than their Euclidean distance.

### Diagnostic Gaussian distance as a function of Euclidean distance

\[
d_{\zeta,\sigma}(w,w')^2
=2\left\{1-\exp\left(-\frac{r^2}{2\sigma^2}\right)\right\},
\qquad
r=\|u_\zeta(w)-u_\zeta(w')\|_2.
\]

**Reading.** Squared diagnostic-kernel feature distance is two times one minus
the Gaussian similarity, where \(r\) is the Euclidean distance between the
two invariant diagnostic vectors.

### Inverting the diagnostic Gaussian distance

\[
r
=\sigma\sqrt{-2\log\left(
1-\frac{d_{\zeta,\sigma}(w,w')^2}{2}
\right)}.
\]

**Reading.** Diagnostic-vector Euclidean distance is recovered exactly from
the nonsaturated diagnostic-Gaussian feature distance. Finite vectors make
that feature distance strictly smaller than \(\sqrt 2\).

## 17. Paired-assignment SUTVA and bounded-odds sensitivity

### Treatment received at each paired position

\[
a_{b0}(z_b)=z_b,
\qquad
a_{b1}(z_b)=1-z_b.
\]

**Reading.** In block \(b\), position zero receives the label recorded by the
assignment bit, while position one receives the complementary label.

### Well-defined versions, no interference, and consistency

\[
Q_{bj}^{\Omega}(z)
=Q_{bj}\!\left\{a_{bj}(z_b)\right\}
\quad\text{for every }b,j,z,
\qquad
q_{bj}=Q_{bj}\!\left\{a_{bj}(Z_b)\right\}.
\]

**Reading.** A well's quotient outcome under the complete assignment schedule
depends only on the condition that well itself receives, and the observed
quotient outcome equals its potential outcome under the realized received
condition. This excludes interference from every other well and treats each
label as one well-defined reagent version.

### Within-pair reindexing

\[
q_{bj}^{\eta}=q_{b,j\mathbin\oplus\eta_b},
\qquad j\in\{0,1\}.
\]

**Reading.** If \(\eta_b=1\), exchange the two stored outcome positions in
block \(b\); if \(\eta_b=0\), leave them unchanged. The symbol \(\oplus\)
means addition modulo two.

\[
T^\eta(z)=T(z\mathbin\oplus\eta)
\quad\text{for every }z\in\Omega.
\]

**Reading.** Computing the statistic after reindexing the stored rows at
assignment \(z\) gives the same value as computing the original statistic at
the bitwise-flipped assignment \(z\oplus\eta\). Because bitwise flipping is a
bijection of all assignments, the complete exact tail count is unchanged. The
symmetric bounded-odds box is also unchanged after replacing \(p_b\) by
\(1-p_b\) in flipped blocks.

### Product bounded-odds assignment model

\[
\frac{1}{1+\Lambda}\le p_b\le\frac{\Lambda}{1+\Lambda},
\qquad
\mathbb P(Z=z\mid\mathcal F)
=\prod_{b=1}^B p_b^{z_b}(1-p_b)^{1-z_b}.
\]

**Reading.** Conditional on the fixed design and potential outcomes, block
assignments remain independent, but the probability of assignment bit one may
depart from one half. Within each block the odds are bounded by the sensitivity
factor \(\Lambda\). This product assumption is stronger than separate marginal
odds bounds and is required for the exact enumeration used here.

### Worst-case sensitivity p-value

\[
\overline p_\Lambda
=
\max_{p_b\in[1/(1+\Lambda),\,\Lambda/(1+\Lambda)]}
\sum_{z\in\Omega}
\mathbf 1\{T(z)\ge T(Z_{\mathrm{obs}})\}
\prod_{b=1}^B p_b^{z_b}(1-p_b)^{1-z_b}.
\]

**Reading.** Among all independent paired-assignment laws allowed by
\(\Lambda\), take the largest probability of obtaining a statistic at least as
large as the observed statistic. Because this probability is affine in every
\(p_b\) separately, its maximum occurs when every probability is at one of its
two allowed endpoints.

### Fixed-law upper-tail p-value

\[
p_p(Z)=\mathbb P_p\{T(Z')\ge T(Z)\mid\mathcal F\},
\qquad Z'\sim\mathbb P_p.
\]

**Reading.** For one admissible assignment-probability vector \(p\), compare
the observed statistic with an independent assignment drawn from that law.
This survival probability is super-uniform under the Fisher sharp null; the
worst-case envelope is no smaller and is therefore also valid.

### Explicit super-uniformity calculation

\[
t_1>\cdots>t_m,
\qquad
\mu_r=\mathbb P_p\{T(Z)=t_r\mid\mathcal F\},
\qquad
s_r=\sum_{j=1}^r\mu_j.
\]

**Reading.** Order the distinct statistic values from largest to smallest.
The mass at level \(t_r\) is \(\mu_r\), and \(s_r\) is the total probability
of that level or any more extreme level. Whenever the observed statistic is
\(t_r\), its upper-tail p-value is \(s_r\). Thus the event that this p-value
is at most \(\alpha\) has probability either zero or the largest cumulative
mass \(s_r\) not exceeding \(\alpha\), proving super-uniformity even with
ties.
