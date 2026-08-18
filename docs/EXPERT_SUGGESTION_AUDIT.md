# Scientific audit of the expert suggestions

Audit date: 31 July 2026. The suggestions were checked against the current
manuscript, frozen RxRx1 results, executable code, and official or primary
sources. They were not accepted merely because they were presented as expert
advice.

## Decisions

| Suggestion | Decision | Scientific reason and action |
|---|---|---|
| The experiments are already exceptionally strong for JASA, JRSS-B, or Biometrika | Rejected as promotional overstatement | The experiment is valuable but has eight primary blocks, one image domain, and an imposed nuisance law. It establishes exact-model robustness, not unrestricted natural-acquisition validity. Journal of Causal Inference remains the defensible first target. |
| Add CAMELYON16/17 as causal validation | Not implemented as a causal result | CAMELYON supplies diagnostic labels, centres, slides, and metastasis annotations, not assigned treatments or potential-outcome schedules. Imposed transformations on its patches could form another semi-synthetic invariance study, but could not independently validate causal treatment-effect identification. Calling centre or tumour status a treatment would be scientifically false. |
| Add ADNI as causal validation | Rejected for the present work | ADNI describes itself as a longitudinal multi-centre observational study; it does not introduce treatments. Access requires an approved account and data-use agreement. Diagnosis is not an intervention, and 3D scanner variation is not an exact rigid-motion action. No ADNI data were accessed or represented as a causal experiment. |
| Add the equation `Y_b(Z)=Y_b(Z_b)` for SUTVA | Accepted after correction | That equation excludes cross-block interference but does not say which reagent each well receives and does not exclude interference from the paired well. The manuscript now gives a well-indexed paired-assignment assumption covering well-defined versions, no interference, and consistency. Every displayed formula is read in `FORMULA_GUIDE.md`. |
| Reword the finite-group canonicalization proof | Accepted | The revised proof constructs the Borel cells of the minimizing index, uses injectivity on distinct orbit points, and handles repeated group indices caused by stabilizers without circular language. |
| Fix missing citation brackets on page 2 | Rejected because the current PDF has no such errors | Every citation command on the current rendered page has its closing bracket. The suggestion appears to refer to an older draft or faulty text extraction; citation numbers are intentionally not hard-coded here because bibliography edits can renumber them. |
| Update preprint references | Partly accepted | Kim and Lee is an ICLR 2026 publication and now points to the official conference page. The current official arXiv records for Bhattacharjee et al., Raykov et al., and Saki and Faghihi list no journal reference, so they remain identified as preprints. |
| Address boundary crops and cite t-SNE | Mathematical issue accepted; citation rejected | t-SNE has no crop-identifiability or incomplete-orbit theorem. The manuscript instead proves a sharp partial-observation theorem: exact recovery is possible precisely when the target is constant on fibers of the combined nuisance-and-observation map. A unit test constructs a crop collision between distinct rigid-motion orbits. |
| Discuss continuous groups as noncompact and lacking Borel sections | Corrected | The rotation group SO(2) is compact. The existing compact-action theorem yields an abstract orbit-valued Borel maximal invariant for a continuous SO(2) action. The larger Euclidean group SE(2) is noncompact, but noncompactness alone does not prove that a maximal invariant is impossible. The unresolved issue here is an exact computable representation for continuously rotated raster data. |
| Prove persistence/Wasserstein stability for the existing Euler endpoint | Rejected as stated; replaced by a valid theorem | Otsu thresholding and component deletion are discontinuous, and fixed-threshold Betti numbers need not be stable. The manuscript now proves bottleneck stability for a separate tame lower-star grayscale filtration and derives the exact nonlinear link to the Gaussian kernel on that invariant diagnostic vector. No unsupported Wasserstein, primary-kernel, or Euler-stability claim is made. |
| Add Rosenbaum bounds for unmeasured confounding | Accepted with a narrower interpretation | The implemented calculation examines hypothetical departure from the reported uniform paired assignment under an explicit independent bounded-odds model. It is not evidence that a verified randomized experiment was confounded. The optimization is exact because the event probability is multilinear and its extrema occur at probability-box vertices. |
| Fit an R-learner for CATE | Rejected for the RxRx1 sample | A standard R-learner requires a scalar response target and adequate sample size. The primary experiment has eight blocks and no prespecified subgroup model. Fitting a flexible learner would be statistically indefensible. The paper instead proves identification for a prespecified integrable scalar invariant functional; no empirical heterogeneous-effect claim is made. |
| Raw pixels and moment registration both fail | Corrected | Raw coordinates fail dramatically under informative acquisition. Moment registration lacks an algebraic invariance guarantee, but the reported simulation null rejection is 0.056 and its acquisition-only control rejects 0 of 200 times. The evidence does not justify saying that it empirically failed in the same way as raw pixels. |

## Implemented extensions

- `src/cqoi/sensitivity.py`: exact product bounded-odds probability bounds and
  numerical sensitivity crossing.
- `src/cqoi/persistence.py`: lower-star zero-dimensional persistence, exact
  bottleneck distance, and Gaussian-metric inversion.
- `scripts/run_expert_review_extensions.py`: hash-audited extension runner with
  a progress bar, elapsed time, ETA, and failure count.
- `scripts/build_extension_results_tex.py`: verifies extension-result hashes
  and generates the manuscript table macros.
- `tests/test_sensitivity.py`, `tests/test_persistence.py`, and
  `tests/test_partial_observation.py`: pair-reindexing checks, an independent
  exhaustive multi-bar bottleneck oracle, and crop-collision counterexamples.
- `results/extensions/`: exact tables, summaries, and an input/output hash
  audit.
- `EXTENSION_METHODS.md`: algorithms, proofs, numerical results, and a reading
  of every formula used in the extensions.

The original confirmatory implementations `experiment.py`, `invariants.py`,
and `statistics.py` were not changed. The extensions are labelled
post-outcome exploratory because the primary result had already been accessed.

## Extension results

- The bounded-odds envelope reproduces the exact paired-swap value 0.0078125
  at sensitivity factor one.
- The exact worst-case upper probability is 0.0391708581 at factor two and
  reaches 0.05 at factor 2.1999953017 under the stated product model.
- All 32 canonical-array and persistence-diagram action-invariance checks
  passed exactly.
- All 32 bottleneck-stability and Gaussian-metric-link checks passed. The
  maximum perturbed bottleneck distance was 0.003917801, below the maximum
  realized sup-norm perturbation 0.003920348.

These values are computational audits under explicit models, not evidence of
robustness to arbitrary acquisition mechanisms.

## Official and primary sources checked

- [Bhattacharjee et al., official arXiv record](https://arxiv.org/abs/2506.22754)
- [Raykov et al., official arXiv record](https://arxiv.org/abs/2503.05024)
- [Kim and Lee, official ICLR 2026 page](https://iclr.cc/virtual/2026/poster/10008398)
- [Saki and Faghihi, official arXiv record](https://arxiv.org/abs/2603.14169)
- [CAMELYON17 official data page](https://camelyon17.grand-challenge.org/Data/)
- [CAMELYON dataset record and DOI](https://gigadb.org/dataset/100439)
- [ADNI official study page](https://adni.loni.usc.edu/)
- [ADNI official data-access page](https://adni.loni.usc.edu/data-samples/adni-data/)

The CAMELYON site currently gives inconsistent licensing statements across its
Data and Download pages. Any future study must resolve the terms for the exact
distribution used and must not redistribute pixels in this package.
