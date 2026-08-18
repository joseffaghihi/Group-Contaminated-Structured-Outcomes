# Changes made for the arXiv release

This file records changes made after auditing the submitted standalone arXiv
source against the complete analysis package. Principal numerical results were
not changed. Changes are grouped by whether they alter scientific statements,
experimental reporting, provenance, or only presentation.

## Scientific and mathematical corrections

1. Strengthened the group assumption in the conditional-Haar result to a
   compact, second-countable Hausdorff topological group with its Borel
   structure.
2. Repaired the nonidentifiability construction by setting the treatment to the
   target value and holding all other observables fixed across the two data
   generating processes.
3. Restored the sharp observability theorem and nonidentifiability corollary for
   partial or lossy acquisition operators, which is needed to interpret the crop
   experiment.
4. Restored formal paired well-defined-version/SUTVA and no-interference
   notation, together with the swap-invariant retention condition.
5. Added the implemented all-equal-distance bandwidth fallback
   (set \(\sigma=1\)) and the fixed conservative \(10^{-12}\) upper-tail
   tolerance.
6. Made explicit that the lattice canonical space is countable and hence
   standard Borel in the characteristic-kernel proof.
7. Replaced unsupported appendix assertions with proofs for the compact-action
   orbit code and finite-group canonical code.
8. Restored the exact bounded-odds sensitivity proposition and proof, clearly
   labeling the analysis as post-outcome and exploratory.

## Experimental and results reporting

1. Replaced hard-coded numerical tables and abstract values with the verified
   generated inputs `results.tex` and `extension_results.tex`.
2. Clarified that 29 checks were the pre-outcome suite and that the final frozen
   scientific package passed 45 of 45 tests.
3. Added exact simulation settings omitted from the standalone rewrite:
   eight-pixel padding, maximum five-pixel shifts, and treatment-channel
   amplitudes \(125\eta\), \(81.25\eta\), and \(43.75\eta\).
4. Defined the moment-registration comparator and described it accurately as a
   diagnostic without the proved maximal-invariant guarantee. It did not fail
   the declared exact-action acquisition-null control; raw pixels did.
5. Restored the exact discovery score, robust normalization, eligibility and
   tie-breaking rules.
6. Restored RxRx1 acquisition details: 16-pixel padding, maximum eight-pixel
   shifts, BLAKE2b generator, seeds 20260731--20260750, and identification of
   seed 20260731 as the realization reported in the primary table.
7. Explained the acquisition-only sharp-null prototype construction.
8. Explained that the approximate-action analysis begins from support-centered
   images, uses opposite site rotations, removes two pixels from every support
   margin, adds within-support Gaussian noise with standard deviation 2, and
   recomputes the pooled bandwidth for each perturbation. The relative feature
   error is now defined explicitly.
9. Restored the prespecified bootstrap audit. Its 10,000 resampled-statistic
   quantiles are reported descriptively and are explicitly not confidence
   intervals or precision bounds.
10. Restored the post-outcome bounded-odds results: exact value 0.0078125 at
    factor 1, worst-case upper probability 0.0391709 at factor 2, and a 0.05
    crossing near 2.1999953.

## Provenance and reproducibility

1. Reran the current 45-test suite, full 1,000-replicate simulation, frozen
   discovery selector, official support-file verification, the complete
   1,920-image integrity acquisition, the 20-seed RxRx1 experiment, and the
   post-analysis extension. Exact comparisons are in `SCIENTIFIC_AUDIT_REPORT.md`
   and `reproducibility/RERUN_AUDIT_2026-08-18.json`.
2. Refreshed `rxrx1_support_integrity.json` against the current frozen selection
   manifest. The previous audit referred to an invalidated historical manifest;
   the official metadata and embedding hashes themselves were unchanged.
3. Corrected the README command for verifying the frozen selection-manifest
   sidecar.
4. Added `CURRENT_ANALYSIS_SOURCE_MANIFEST.sha256`, covering all Python source,
   scripts, tests and the dependency specification. Its own digest is embedded
   in the manuscript through `release_audit.tex`.
5. Added `scripts/audit_arxiv_release.py`, a separate release check that verifies
   the generated numerical inputs and figure, rejects build artifacts, and can
   compile the standalone source in an isolated directory.

## Editorial and packaging

1. Updated the RxRx1 citation from the arXiv preprint to the formal CVPR
   Workshops 2023 publication and DOI.
2. Replaced the repository-placeholder wording with an exact description of the
   companion archive and the fact that licensed raw images are reacquired rather
   than redistributed.
3. Used a fixed August 2026 manuscript date instead of a dynamic compilation
   date.
4. Updated the caption list for all seven tables.
5. Corrected the arXiv README and specified either `latexmk -pdf` or three clean
   `pdflatex` passes.
6. Removed arXiv build artifacts from the upload source. The source archive
   contains only the main TeX, three generated TeX inputs, the generated figure,
   and README.

## Numerical disposition

- No displayed simulation rejection fraction, confidence interval, RxRx1 MMD
  statistic, exact p-value, Holm-adjusted value, acquisition-null count, or
  approximate-action result required correction.
- The primary inference remains the canonical-quotient paired-swap result
  \(\widehat{\mathrm{MMD}}_u^2=0.003644\) with
  \(p=2/256=0.0078125\).
- The simulation result remains size 0.052 at \(\eta=0\) and power 0.992 at
  \(\eta=1\) for the exact quotient method.
- Newly restored tables add transparent audit and robustness information; they
  do not redefine or replace the frozen primary endpoint.
