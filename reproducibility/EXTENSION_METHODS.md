# Post-analysis sensitivity and stable-persistence extension

These analyses were fixed in
`data/manifests/post_rxrx1_expert_review_extension.json` after the primary
RxRx1 outcome analysis. They are therefore reported as post-outcome
diagnostics, not as additional confirmatory tests.

For the sensitivity calculation, wells within each experiment block are
ordered by ascending `well_id`, without using the treatment label. The
reconstructed statistic and exact p-value are checked against the frozen
condition-indexed computation. Within-pair reindexing induces a bitwise-XOR
bijection on the complete assignment space and the symmetric probability box,
so both the exact tail count and the bounded-odds envelope are unchanged.

## Exact Rosenbaum bounds for the paired MMD test

Let $Z_b\in\{0,1\}$ encode which well in experiment block $b$ receives
label one. Under the sensitivity model, the eight assignment bits are
conditionally independent and

\[
  \frac{1}{1+\Lambda}\leq p_b
  :=\Pr(Z_b=1\mid\mathcal F)\leq
  \frac{\Lambda}{1+\Lambda},\qquad b=1,\ldots,8.
\]

Read: “Conditional on the fixed outcomes and matched blocks, the probability
of either within-block assignment may be biased, but the orientation odds are
bounded by the sensitivity factor Lambda.”

For the one-sided randomization tail
$\mathcal E=\{z:T(z)\geq T(z_{\mathrm{obs}})-10^{-12}\}$, its probability is

\[
  p_{\boldsymbol p}(\mathcal E)
  =\sum_{z\in\mathcal E}\prod_{b=1}^{8}
    p_b^{z_b}(1-p_b)^{1-z_b}.
\]

Read: “The tail probability is the sum, over assignments at least as extreme
as the observed assignment, of the product Bernoulli probability of each
assignment.”

### Vertex theorem

The minimum and maximum of $p_{\boldsymbol p}(\mathcal E)$ over the Lambda
box occur at box vertices, so exact bounds require only $2^8$ event
assignments and $2^8$ probability vertices.

Proof. Holding seven coordinates fixed, the displayed polynomial is affine in
the remaining coordinate $p_b$. An affine function on a closed interval
attains both extrema at an endpoint. Move one coordinate of any extremizer to
an endpoint without worsening the relevant objective and repeat for all eight
coordinates. The resulting extremizer is a box vertex. Because both finite
sets are exhaustively enumerated by the software, the reported bounds are
exact up to floating-point evaluation of finite sums. 

At $\Lambda=1$, both endpoints equal one half, so the lower and upper bounds
equal the original exact randomization p-value, $2/256=0.0078125$. The
enumerated tail contains only the observed assignment and its global label
complement. Consequently, for this dataset the upper bound also has the closed
form

\[
 \overline p_\Lambda=\frac{\Lambda^8+1}{(1+\Lambda)^8}.
\]

Read: “The numerator is Lambda to the eighth plus one, and the denominator is
the eighth power of one plus Lambda.”

Indeed, let $k$ be the number of endpoint choices aligned with the observed
assignment, meaning that the chosen endpoint makes the observed bit more
probable. The two complementary tail assignments then have numerator
$\Lambda^k+\Lambda^{8-k}$; convexity in $k$ makes it largest at $k=0$ or
$k=8$. Thus the worst-case upper p-value is 0.0391708581 at $\Lambda=2$, and
it first reaches 0.05 at $\Lambda\approx2.19999530$ under this model.

## Stable zero-dimensional persistence on canonical images

The original thresholded-and-cleaned Euler signature is not used for a
stability claim: hard thresholding and component removal are discontinuous.
The extension instead computes zero-dimensional persistent homology of the
lower-star filtration of the fixed four-neighbour grid on a 16 by 16
normalized canonical nuclear-channel image.

### Bottleneck stability theorem

For two real-valued functions $f,g$ on the same finite pixel grid,

\[
  d_B\!\left(D_0(f),D_0(g)\right)
  \leq \lVert f-g\rVert_\infty.
\]

Read: “The bottleneck distance between the zero-dimensional persistence
diagrams is at most the largest absolute pixel perturbation.”

Proof. Put $\varepsilon=\lVert f-g\rVert_\infty$. For every threshold $t$,
$f(v)\leq t$ implies $g(v)\leq t+\varepsilon$, and conversely with $f$
and $g$ exchanged. These inclusions extend from vertices to their lower-star
cubical subcomplexes and commute with the filtration maps. Hence the two
finite persistence modules are $\varepsilon$-interleaved. Finite persistence
modules are q-tame, so the algebraic stability/isometry theorem yields the
displayed bottleneck bound. 

For flattened 16-by-16 resampled invariant diagnostic arrays $x,y$, the
diagnostic Gaussian kernel with bandwidth $\sigma>0$ gives RKHS feature
distance

\[
 d_k(x,y)^2=2\left\{1-
 \exp\!\left(-\frac{\lVert x-y\rVert_2^2}{2\sigma^2}\right)\right\}.
\]

Read: “The squared distance between Gaussian-kernel feature maps is two times
one minus the Gaussian similarity of the two images.”

Whenever $d_k(x,y)<\sqrt 2$, inversion gives

\[
 \lVert x-y\rVert_2
 =\sigma\sqrt{-2\log\!\left(1-\frac{d_k(x,y)^2}{2}\right)}.
\]

Read: “The Euclidean image distance equals bandwidth times the square root of
minus twice the logarithm of one minus half the squared RKHS distance.”

Combining norm monotonicity and stability gives

\[
 d_B\!\left(D_0(x),D_0(y)\right)
 \leq\lVert x-y\rVert_\infty
 \leq\lVert x-y\rVert_2
 =\sigma\sqrt{-2\log\!\left(1-d_k(x,y)^2/2\right)}.
\]

Read: “Persistence discrepancy is bounded by the sup-norm discrepancy, then
by Euclidean discrepancy, which is exactly recoverable from the nonsaturated
Gaussian feature distance.”

For all 32 primary-pair sites, canonical images and persistence diagrams were
exactly unchanged by the recorded treatment-dependent lattice action. For all
32 independently perturbed diagnostic images, the computed bottleneck
distance obeyed the displayed bound. The maximum bottleneck distance was
0.003917801, while the maximum realized sup-norm perturbation was 0.003920348.

## Reproduction

Run `python scripts/run_expert_review_extensions.py`. Its terminal progress bar
reports completion fraction, elapsed time, ETA and failure count. The script
writes exact tables, summaries and an input/output hash audit under
`results/extensions/` without changing any frozen primary-analysis module or
result.
