# Scientific and computational audit report

**Manuscript:** *Causal inference for group-contaminated structured outcomes:
observable quotients, lossless reduction and exact randomization inference*  
**Audit date:** 2026-08-18  
**Audited submission:** uploaded standalone arXiv source  
**Reference implementation:** companion `reproducibility/` directory

## Executive conclusion

The uploaded arXiv ZIP contained the standalone manuscript and local TeX build
artifacts but no analysis code. The code audit and reruns therefore used the
complete companion reproducibility archive, and the final release now packages
that code together with the corrected arXiv source.

The principal numerical findings in the uploaded arXiv version agree with the
frozen machine-readable outputs at every displayed precision. The full current
simulation reproduced the archived CSVs byte for byte, and the code-generated
simulation PNG reproduced byte for byte. The full real-image rerun disposition
is recorded below. The audit found reporting and provenance defects, but no
error that changes the primary or secondary numerical conclusions.

The central mathematical claims are sound after the corrections listed in
`CHANGES.md`. In particular, the observability/factorization results, the
lossless-reduction boundary, the conditional-Haar special case, the
product-versus-diagonal distinction, the conditional approximate-action bound,
the lattice maximal invariant, the characteristic quotient kernel and the
complete paired-randomization validity argument are mutually consistent. The
revised paper now states the topological and causal assumptions needed by those
arguments and proves the appendix constructions that had been compressed into
unsupported assertions.

This is a scientific and reproducibility audit, not peer review or external
validation of the original RxRx1 assignment mechanism. Remaining assumptions
and interpretation limits are stated explicitly in the manuscript and below.

## Numerical comparison

| Quantity | Frozen/output value | Revised paper | Disposition |
|---|---:|---:|---|
| Simulation quotient size, \(\eta=0\) | 13/250 = 0.052 | 0.052 | unchanged |
| Exact 95% binomial interval | 0.0280--0.0873 | 0.0280--0.0873 | unchanged |
| Simulation quotient power, \(\eta=1\) | 248/250 = 0.992 | 0.992 | unchanged |
| Primary quotient statistic | 0.003644 | 0.0036 displayed | unchanged |
| Primary exact paired-swap p-value | 2/256 = 0.0078125 | 0.0078 displayed | unchanged |
| Euler diagnostic statistic/p | 0.753540 / 0.0078125 | 0.7535 / 0.0078 | unchanged; unadjusted secondary |
| Moment-registration statistic/p | -0.006536 / 0.2109375 | -0.0065 / 0.2109 | unchanged; diagnostic |
| Raw-pixel statistic/p | 0.166439 / 0.0078125 | 0.1664 / 0.0078 | unchanged; diagnostic |
| Secondary family | 0/9 survive Holm | 0/9 survive Holm | unchanged |
| Acquisition-null quotient/Euler/moment | 0/200 each | 0/200 each | unchanged |
| Acquisition-null raw pixels | 200/200 | 200/200 | unchanged |
| Exact invariance audit | 0 failures / 6,400 | 0 / 6,400 | unchanged |
| Bounded-odds upper p at factor 2 | 0.0391709 | 0.039171 | restored, not newly computed |
| Bounded-odds 0.05 crossing | 2.1999953 | 2.199995 | restored, exploratory |

All 16 simulation table fractions, four null intervals, ten RxRx1 pair rows,
all Holm values, four acquisition-null rows and 20 approximate-action rows were
also compared directly and agreed at the displayed precision.

## Executed checks and reruns

### Static and unit-level verification

- Frozen scientific suite: **45/45 passed**.
- Historical pre-outcome suite: 29/29; the uploaded rewrite had reported only
  this older count.
- Both numerical TeX builders reproduced the archived `results.tex` and
  `extension_results.tex` byte for byte.
- Standalone arXiv release audit: generated inputs byte-identical, generated
  figure byte-identical, no forbidden build artifacts, and isolated LaTeX
  compilation passed.
- Final manuscript: 25 pages, no undefined references/citations, no overfull or
  underfull boxes, and every page visually inspected after rendering.

### Full simulation rerun

- 1,000 algebraic orbit-audit trials plus 1,000 Monte Carlo replicates.
- Runtime: 255.77 seconds.
- Failures: zero.
- `simulation_replicates.csv` SHA-256:
  `c8b0bc524063ef6725bcce37dcbff410c957a03edb500226288a32b9a6374049`
  (byte-identical to frozen output).
- `simulation_summary.csv` SHA-256:
  `409c66680379e04d8a34494aec901690c1f77eb73edaeb45d682999322a329f9`
  (byte-identical to frozen output).
- Rebuilt PNG SHA-256 matched the archived PNG exactly. The PDF plot may differ
  only in container metadata; its rendered content is the same.

### Discovery and data-integrity reruns

- Discovery-only selector runtime: 3.76 seconds.
- All ten ordered pairs, scores, plate maps and tie-break ordering matched the
  frozen selection. Differences were limited to run timestamp/path provenance
  and the current selector source hash.
- Official support verification passed with zero failures:
  - metadata: 10,094,584 bytes,
    SHA-256 `799ed719d2be136db29fef6fcb7a51ceb94d1de9d43421a49b16409329a2f1b7`;
  - embeddings: 172,102,542 bytes,
    SHA-256 `e38f50b74c45682ec9ce7e6407b891c953c27217be5e39b187d289320395a192`.
- All 1,920 required PNGs were reacquired from the official archive by range
  extraction. Every PNG passed size, CRC32, SHA-256 and signature gates. Every
  path, byte size, CRC32, SHA-256, order, aggregate digest and total byte count
  matched the archived integrity record; only completion time, downloaded/reused
  counts and absolute local paths differed.

### Full RxRx1 and extension reruns

- Complete RxRx1 experiment: 20 nuisance seeds, 223 tracked analysis steps plus
  the 1,920-file preflight, 228.573 seconds, return code 0, zero failures.
- All six scientific CSVs were byte-identical to the archive:
  - `pair_seed_results.csv`: `7daf049b643a869f77ee5aaee3cdee15644ea7805c16a55052217b85f2420626`;
  - `acquisition_null_results.csv`: `6a093b8768ff16263fe009b46d1333fd6fc52bb336ead5ddf1452c38e07ab632`;
  - `acquisition_null_false_positive_summary.csv`:
    `6b4f67c5dd3ec449c13cefccc4db7f844230ddbf56cfae8f9cd210f691238427`;
  - `approximate_action_stress.csv`:
    `bf300147876cb8635679fedb2eb833d76e63119f856fb25bd89c2b37a6a66ade`;
  - `clean_contaminated_equivalence.csv`:
    `239d950bee3676e5d55bf2c6773720400191362134ef62ee59ccdd8cb0603a3e`;
  - `hidden_nuisance_truth_NOT_ANALYSIS.csv`:
    `ae2cc341dc9e05fc2e8f48a38b7e1383fba63c278fa85d9153b0f2875e00fd75`.
- The RxRx1 PNG was byte-identical to the archived figure
  (`d831d0b2...`). The two PDFs differed only in container metadata and rendered
  byte-identically at 150 dpi.
- The experiment-summary scientific configuration, output hashes and analysed
  source hashes were identical. Differences were limited to timestamp, absolute
  paths, Python build string and host platform.
- Post-analysis extension: 252 tracked steps, 2.649 seconds, return code 0,
  zero failures. The sensitivity CSV, persistence CSV and both scientific
  summary JSON files were byte-identical to the archive.
- Core generated TeX built entirely from the fresh simulation and RxRx1 outputs
  was byte-identical to `paper/results.tex`, SHA-256
  `7dd075b2d5ce0eabc3515d950381278beb7d93426e31d3a71971c4f6a4a96be1`.
- Extension TeX from the fresh audit changed only
  `RxExtensionAuditHash`, because the refreshed audit JSON correctly records new
  run provenance. Every numerical macro was identical. When the builder was run
  from the fresh scientific outputs with the frozen provenance audit, the TeX
  was byte-identical to `paper/extension_results.tex`, SHA-256
  `92d06e0e5a0049d5827be14080211fba232dc5248c4477289a76fb3f1935e37b`.
- Environment: Python 3.12.13, NumPy 2.3.5, pandas 2.2.3, SciPy 1.17.0,
  Matplotlib 3.10.8 and Pillow 12.3.0. The package pins Pillow 12.2.0; the
  patch-level difference had no numerical or image-output effect because every
  image-derived scientific CSV and PNG reproduced byte for byte.

## Paper-to-code consistency corrections

The uploaded standalone TeX hard-coded its tables and was not covered by the
analysis package's results-builder tests. The revision now consumes generated
macros. The separate release checker additionally confirms the following:

1. `results.tex` equals the analysis-generated core numerical input byte for
   byte;
2. `extension_results.tex` equals the generated extension input byte for byte;
3. all critical result/table macros are referenced by the manuscript;
4. `simulation_power.pdf` equals the code-generated figure byte for byte;
5. the source directory contains no `.aux`, `.log`, `.out`, `.synctex.gz`,
   LaTeX-work database or operating-system metadata files;
6. the upload source compiles in an isolated directory.

## Important interpretation limits retained in the revision

1. **Imposed acquisition law.** The images and biological batch structure are
   real RxRx1 data, but the treatment- and outcome-dependent transformations are
   imposed for this controlled unknown-acquisition experiment. The paper does
   not claim they reconstruct the original microscope's latent motion.
2. **Assignment law.** Public documentation says siRNA locations were randomized
   separately by experiment and plate, and the metadata confirms same-stratum
   pairing. The metadata alone cannot prove uniform probabilities. The primary
   exact test is conditional on the declared paired-swap mechanism; the
   post-outcome bounded-odds calculation is an exploratory robustness analysis.
3. **Embedding independence.** Discovery uses only discovery rows, but the public
   embedding generator may have been trained using wider data. Complete
   algorithmic independence from confirmation images is therefore an assumption.
4. **Moment registration.** It is a diagnostic without a proved maximal-invariant
   guarantee. It was empirically exact under the declared lattice action and did
   not exhibit acquisition-null false positives; only raw pixels failed that
   control.
5. **Bootstrap quantiles.** The 10,000 paired-block bootstrap draws are retained
   only as descriptive resampled-statistic quantiles. Duplicate sampled blocks
   change the U-statistic's diagonal structure, so those quantiles are not
   reported as confidence intervals.
6. **Approximate transformations.** The approximate-action theorem is conditional
   on metric and kernel Lipschitz properties not established globally for the
   lexicographic canonicalizer. The rotations, crop and noise experiment is an
   empirical stress test, not a validation of that theorem.
7. **Cropping.** A field-of-view crop is a lossy observation operator. Small
   empirical sensitivity under the frozen two-pixel crop cannot restore
   identifiability for arbitrary partial observation.
8. **Multiplicity and scope.** The quotient-pixel contrast is the sole primary
   test. Euler is an unadjusted secondary endpoint; nine additional contrasts
   are a Holm-adjusted secondary family; moment and raw pixels are diagnostics.
   The estimand is reagent-specific, not automatically gene-specific.

## Provenance

- Frozen selection-manifest SHA-256:
  `b6f350ca96fb9e7a6271845dd6e432ed9dca556144a1a332d8f5af168642b968`.
- Legacy core-source fingerprint retained for historical continuity:
  `source-e9f042c387cf`.
- Complete current analysis-source manifest SHA-256:
  `f776624d9ad56525a4b39ecd418687b2867ae981f7ef6da7d8d5ad63da736a1d`.
- The complete path-by-path manifest is
  `reproducibility/CURRENT_ANALYSIS_SOURCE_MANIFEST.sha256`.

## Submission disposition

After the listed corrections and completion of the full current-source rerun,
the package is internally consistent and suitable for arXiv submission. The
authors should still perform the ordinary final author checks: approve the exact
wording and AI-use disclosure, confirm the RxRx1 licence obligations, and decide
where the companion reproducibility archive will be publicly deposited. The
recovered code package did not include a software licence; none was invented
during this audit, so the authors should select and add one before public code
distribution.
