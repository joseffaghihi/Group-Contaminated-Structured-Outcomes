# Reproducibility and release audit

> This audit records the original complete release. References below to
> manuscript source or LaTeX build files describe that audited release; those
> files are intentionally not part of this code-and-results repository.

## Release status

The manuscript, formula guide, source code, frozen manifests, simulations,
RxRx1 confirmation analysis, and explicitly post-outcome robustness extension
are complete. The final PDF is required to compile without LaTeX warnings,
undefined citations or references, underfull boxes, or overfull boxes, and
every final page is rendered with Poppler and visually inspected before
release.

Two independent read-only audits were completed before the held-out RxRx1 run:

- mathematical/editorial audit: pass;
- statistical/freeze-integrity audit: pass.

The dependency-free test runner passed 29 of 29 checks before the held-out
analysis and again immediately after it. After adding isolated sensitivity,
persistence, partial-observation, and extension-builder tests, the expanded
suite passes 45 of 45 checks. The current progress-record hash is reported in
the final artifact hash table below.
The pre-analysis amendment records the earlier passing run's progress hash
`0a07fc1c5383f572cbaf277fc54fdac5354122d08ba38e8d483cd6c2162b77ee`;
the atomic progress file was overwritten by the final rerun, while its test
count and zero-failure status were unchanged.

## Frozen design and data gates

- Discovery rows: HUVEC-01 through HUVEC-12.
- Unused reserve: HUVEC-13 through HUVEC-16.
- Confirmation images: HUVEC-17 through HUVEC-24.
- Primary contrast: siRNA 384 (`s38230`) versus siRNA 747 (`s37149`).
- Secondary family: nine disjoint, prespecified contrasts.
- Frozen selection manifest SHA-256:
  `b6f350ca96fb9e7a6271845dd6e432ed9dca556144a1a332d8f5af168642b968`.
- Confirmation subset: 160 wells, 320 sites, 1,920 six-channel PNG files,
  totaling 117,421,323 bytes.
- Every PNG passed archive-size, CRC32, SHA-256, and PNG-signature checks.
- Missing, extra, partial, failed, and quarantined PNG counts were all zero.
- Image-integrity manifest SHA-256:
  `b2dbcb9590fa89c1e90795f6265ef22f2c34f6e4b2a93003b24281e24ebee591`.
- The downloader and analysis runner independently enforce the metadata digest
  frozen in the selection manifest.
- The runner rehashed all 1,920 PNGs before reading outcomes.

The public metadata support the same-plate/completeness gate and report
within-experiment, within-plate randomization. They do not expose the original
randomization log. Consequently, finite-sample causal validity is conditional
on the explicit uniform paired-assignment premise stated in the paper.

## Simulation

The frozen simulation used 250 independent replicates at each of four effect
strengths, eight randomized blocks per replicate, all 256 paired assignments,
and 1,000 separate orbit-invariance trials.

- Exact quotient null rejection fraction: 0.052; exact 95% binomial interval
  0.0280 to 0.0873.
- Finite Euler null rejection fraction: 0.040; exact 95% binomial interval
  0.0193 to 0.0723.
- Raw-coordinate diagnostic null rejection fraction: 1.000.
- Moment-registration diagnostic null rejection fraction: 0.056.
- Exact quotient rejection fraction at effect strength 1: 0.992.
- Invariance audit: 1,000 of 1,000 passed.

An isolated full-default rerun produced byte-identical replicate and summary
CSVs. The reproduction audit SHA-256 is
`80ce0484034c42b3ba975e1a037d81e96ea0dd5b29d7778e9df321b6c065e916`.

## RxRx1 held-out analysis

The frozen run completed in 7 minutes 34 seconds with no failure.
Transformation parameters were generated and logged separately but were not
supplied to a representation or test.

Across 20 frozen treatment- and outcome-dependent acquisition realizations:

- exact quotient maximum clean-versus-transformed feature error: 0;
- finite Euler maximum clean-versus-transformed feature error: 0;
- exact quotient maximum statistic and p-value changes: 0;
- finite Euler maximum statistic and p-value changes: 0;
- full exact-invariance audit: 6,400 of 6,400 passed.

For the sole primary canonical-quotient test:

- MMD statistic: 0.003644;
- complete paired-swap p-value: 0.0078125;
- assignments enumerated: 256.

The finite Euler p-value of 0.0078125 is an unadjusted secondary result. Raw
and moment-registration p-values are diagnostics, not confirmatory causal
tests. None of the nine canonical-quotient secondary contrasts remained
significant after Holm familywise adjustment; the smallest adjusted p-value
was 0.0703125.

In the acquisition-only sharp-null control over 10 contrasts and 20 nuisance
seeds, the exact quotient, finite Euler, and moment-registration procedures
rejected 0 of 200 times. Raw coordinates rejected 200 of 200 times. Because
pair-seed evaluations share biological blocks, the displayed binomial
intervals are descriptive summaries rather than independent-trial coverage
claims.

The approximate-action audit used interpolated rotations, support truncation,
and within-support noise. It is a sensitivity analysis outside the exact
lattice action, not evidence of exact invariance to those perturbations.

## Bootstrap reporting correction

The prespecified analysis generated 10,000 paired-block bootstrap replicates
for the four primary-pair representations. Resampling eight block identifiers
with replacement creates duplicate observations; applying the conventional
observation-level U-statistic to duplicated rows changes its
diagonal-exclusion structure. All four original statistics fell below the
corresponding empirical 2.5th percentile.

No statistic was recomputed or replaced. The frozen values are retained and
labeled only as the empirical 2.5th and 97.5th percentiles of the resampled
statistic. They are not confidence intervals or precision bounds. The
post-analysis reporting amendment has SHA-256
`c2cdd37c348e90fad28156b5b2727c9b906c284b49390e170a243f771aa7579b`.

## Post-analysis expert-review extensions

The primary outcome and confirmatory result had already been accessed before
these analyses were specified. The extension manifest therefore labels them
`post_outcome_exploratory_extension`; neither result is presented as
confirmatory. The manifest SHA-256 is
`3b01ac7cbea15a648ee1a2dac380ebb75bc841c083686a27d0b31a96ea16f458`.

The bounded-odds calculation orders the two wells in each experiment block by
ascending well ID, without treatment labels, and reproduces the frozen
condition-indexed statistic and exact p-value. It assumes conditional
independence of the eight paired assignment bits and permits their
probabilities to vary inside the stated probability box. It enumerates every
assignment and every box vertex.

- At sensitivity factor 1, the upper envelope is 0.0078125, exactly matching
  the complete paired-swap value.
- At factor 2, the worst-case upper value is 0.0391708581.
- The upper value first reaches 0.05 at factor 2.1999953017.

This quantifies hypothetical departure from uniform assignment under the
product model; it is not evidence that an unmeasured confounder existed.

The stable topology diagnostic uses lower-star zero-dimensional persistence on
a 16-by-16 resampled invariant nuclear-channel representation and its own
Gaussian kernel, not the primary full-image kernel or the thresholded finite
Euler signature.

- All 32 canonical-array and diagram invariance checks passed exactly.
- All 32 bottleneck-stability and Gaussian-metric-link checks passed.
- The maximum exact-action bottleneck distance was zero.
- The maximum perturbed bottleneck distance was 0.003917801, below the maximum
  realized sup-norm perturbation 0.003920348.

Before rerunning the extension, the runner reverified all 192 primary PNGs
against the frozen image-integrity manifest and rehashed the metadata,
selection, original results, nuisance record, and analysis sources. The
original confirmatory modules retain their frozen hashes. The expanded tests
include an independent exhaustive diagonal-augmented bottleneck oracle for
multi-bar diagrams and a within-pair row-flip invariance check.

## Principal artifact hashes

| Artifact | SHA-256 |
|---|---|
| `paper/main.pdf` | `9ba523023f417b449b680e56f0824ce8414f085c67a92aa336dd700dc10315f8` |
| `paper/main.tex` | `b633e1cdb45af06ca45b08c851defb7080d1af6d57dafda5de608d31afb36b5b` |
| `paper/results.tex` | `7dd075b2d5ce0eabc3515d950381278beb7d93426e31d3a71971c4f6a4a96be1` |
| `paper/extension_results.tex` | `92d06e0e5a0049d5827be14080211fba232dc5248c4477289a76fb3f1935e37b` |
| `FORMULA_GUIDE.md` | `89c7d9b0401ddfa97812cd9595b3d1317b65ac276268fc27d102a5d5cc9fa94e` |
| test progress record (45/45) | `a7194096ffa0ceb64f9a2d78403299ee2b91ba7b02df0b9ea303edb23d818e95` |
| extension progress record (252/252) | `ce37f2274134d6ce3783a0624b855c1611a5f6e7b42af634e417908e6ca55083` |
| extension input/output audit | `7928f075dd02630e2c735a89bbd64e8a76f8b9191b2785cfe8de6542462c0882` |
| simulation replicates | `c8b0bc524063ef6725bcce37dcbff410c957a03edb500226288a32b9a6374049` |
| simulation summary | `409c66680379e04d8a34494aec901690c1f77eb73edaeb45d682999322a329f9` |
| RxRx1 pair-seed results | `7daf049b643a869f77ee5aaee3cdee15644ea7805c16a55052217b85f2420626` |
| RxRx1 experiment summary | `669d7343ab5fec2275a4a622ec8d36260ac634670c98a086189d4b04bdd942e0` |
| exact analysis implementation | `da741a882bc8ee176d5655c1c1ebf50467a465d7fb7a9e448dd83131d53c557e` |
| exact-test implementation | `3b597db2171c002915a54b501f9337383e5591388cf5715d76cd407fc1a2b965` |
| sensitivity implementation | `c7598216e757979230bbe4f781aba2d120e67b90c34cc92d472dd255c8b36a0b` |
| persistence implementation | `1d642c83da2c9912608bf0c9a3bc91b19fcc4a731be7b9bc2036ffb46902c8ed` |
| extension runner | `628f35e927f4591372075d7143c1fd7a76596f65c3e9b6f5329ade57f5d88c1a` |

Raw RxRx1 images, metadata, embeddings, and source ZIP files are excluded from
the distributable archive because they are externally licensed data. The
download and integrity scripts reproduce and verify them from the official
source.
