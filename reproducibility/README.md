# Causal inference for group-contaminated structured outcomes

This repository contains the manuscript, proofs, frozen analysis protocol, and
reproducible experiments for causal inference when a structured outcome is
recorded after an unknown sample-specific group transformation. The concrete
benchmark uses two-site, six-channel RxRx1 microscopy wells. Each site receives
its own treatment- and outcome-dependent integer translation and quarter-turn
rotation. Realized transformation parameters are excluded from estimator
inputs, and the well remains the sole inferential unit.

The scientific disposition of the later expert suggestions is recorded in
[`EXPERT_SUGGESTION_AUDIT.md`](EXPERT_SUGGESTION_AUDIT.md). Detailed proofs,
algorithms, numerical values, and formula readings for the post-analysis
extensions are in [`EXTENSION_METHODS.md`](EXTENSION_METHODS.md); readings for
all manuscript displays are in [`FORMULA_GUIDE.md`](FORMULA_GUIDE.md).

The standalone submission source is in [`paper/arxiv`](paper/arxiv) in the
complete release bundle. It consumes the generated `paper/results.tex` and
`paper/extension_results.tex` inputs rather than duplicating numerical values.
Run the release-level consistency and compile audit with:

```bash
python scripts/audit_arxiv_release.py --compile
```

This release audit is separate from the frozen 45-test scientific suite.

The confirmatory representation is an explicit maximal invariant for the
product action

\[
(\mathbb Z^2\rtimes C_4)^2.
\]

Each site is support-normalized and then mapped to the lexicographically least
member of its four quarter-turn orbit. The two ordered site codes are
concatenated at the well level. Inference compares treatment-specific quotient
laws with an RBF-kernel MMD statistic and enumerates all \(2^8=256\)
within-experiment label swaps. A finite eight-direction Euler characteristic
transform, moment registration, and raw pixels are prespecified secondary or
diagnostic representations.

## Reproducibility status

The design uses a discovery–confirmation split:

- HUVEC-01 through HUVEC-12: discovery embeddings only;
- HUVEC-13 through HUVEC-16: unused reserve;
- HUVEC-17 through HUVEC-24: row-level image confirmation;
- 10 disjoint same-plate siRNA pairs: one primary and nine prespecified
  secondary contrasts;
- 20 frozen hidden-acquisition seeds: 20260731 through 20260750;
- seed 20260731 is the primary acquisition realization; the other 19 are
  robustness realizations;
- 10,000 paired-block bootstrap resamples for a descriptive
  bootstrap-statistic quantile audit, not confidence intervals;
- complete \(2^8\) paired-swap distributions for every reported \(p\)-value;
- Holm adjustment across the nine secondary contrasts.

After the confirmatory outcome analysis, an explicitly post-outcome extension
was fixed and executed. It adds an exact bounded-odds sensitivity envelope for
possible departure from uniform paired assignment and a stable lower-star
persistence diagnostic. These extensions do not alter or relabel the frozen
primary analysis.

The frozen, hash-recorded selection and the documented pre-outcome amendments are in
[`data/manifests`](data/manifests). Their timestamps, hashes, and outcome-access
statements record the analysis chronology; the adjacent hashes are integrity
checks, not externally timestamped preregistrations. Do not overwrite the
frozen selection manifest.

## Environment

The code was run with Python 3.12 and requires:

- NumPy
- pandas
- SciPy
- Pillow
- Matplotlib
- a LaTeX installation with `pdflatex` and `bibtex`

No `pytest` installation is required. The repository includes a small
dependency-free test runner.

## Official RxRx1 support files

RxRx1 is released by Recursion through the
[official dataset page](https://www.rxrx.ai/rxrx1) and described in the
[official dataset README](https://github.com/recursionpharma/rxrx-datasets/tree/trunk/rxrx1).
The support-file fetcher uses the public Google Cloud Storage JSON API
`alt=media` endpoints for the official objects:

- `rxrx1/rxrx1-metadata.zip`
- `rxrx1/rxrx1-dl-embeddings.zip`

Google documents this media-download form in its
[Cloud Storage JSON API object-download documentation](https://cloud.google.com/storage/docs/json_api/v1/objects/get).

From the repository root, fetch or verify the metadata and embeddings:

```bash
python scripts/fetch_rxrx1_support_files.py
```

The default extracted layout is:

```text
../data/raw/rxrx1/
├── rxrx1-metadata.zip
├── rxrx1-dl-embeddings.zip
└── rxrx1/
    ├── metadata.csv
    └── embeddings.csv
```

Downloads are resumable, written to `.part` files, ZIP-validated, extracted to
temporary files, and atomically renamed. An extracted file is accepted only if
its SHA-256 equals the digest recorded in
[`selection_manifest.json`](data/manifests/selection_manifest.json):

```text
metadata.csv    799ed719d2be136db29fef6fcb7a51ceb94d1de9d43421a49b16409329a2f1b7
embeddings.csv  e38f50b74c45682ec9ce7e6407b891c953c27217be5e39b187d289320395a192
```

To prohibit network access and verify an existing local copy:

```bash
python scripts/fetch_rxrx1_support_files.py --verify-only
```

The verification audit is written atomically to
`data/manifests/rxrx1_support_integrity.json`.

RxRx1 is distributed under the license linked from the official dataset page.
Users are responsible for complying with its attribution,
non-commercial-use, and share-alike terms.

Raw RxRx1 ZIPs, CSVs, and PNGs are external licensed data. They are not part of
the manuscript artifact and must not be committed to, or redistributed with,
this repository. The reproducible deliverables are the code, frozen manifests,
integrity digests, derived numerical tables, and figures.

## Reproduction workflow

Run commands from this directory.

### 1. Verify the frozen manifest

```bash
(cd data/manifests && sha256sum -c selection_manifest.json.sha256)
python scripts/fetch_rxrx1_support_files.py --verify-only
```

The frozen discovery-only selection manifest SHA-256 is:

```text
b6f350ca96fb9e7a6271845dd6e432ed9dca556144a1a332d8f5af168642b968
```

The selection rule can be independently rerun to an alternate path, without
modifying the frozen manifest:

```bash
python scripts/select_rxrx1_pair.py \
  --manifest /tmp/rxrx1_selection_reproduction.json
```

Selection reads only HUVEC-01 through HUVEC-12 embedding and metadata rows.
Confirmation completeness and same-plate occurrence are checked afterward as
analysis gates and do not alter the frozen condition list. A prior
completeness-filtered implementation produced exactly the same ordered list and
scores and is retained under `data/manifests/invalidated`.

### 2. Fetch the confirmation image subset

```bash
python scripts/fetch_rxrx1_subset.py
```

This range-downloads exactly 1,920 PNGs: 10 pairs × 2 conditions × 8
experiments × 2 sites × 6 channels. Existing files are reused only after
remote CRC verification. The final pass verifies size, CRC32, SHA-256, PNG
signature, absence of missing files, and absence of extra PNGs.

### 3. Run the tests

```bash
python scripts/run_tests.py
```

The final expanded suite contains 45 tests. The earlier 29-test count records
the pre-outcome suite before the robustness extensions were added.

The tests cover product-action invariance with different motions at the two
sites, known planar Euler characteristics, exact enumeration of 256
assignments, the true Fisher sharp-null simulator, small-seed calibration,
results-macro completeness, offline support-file verification, exact
bounded-odds vertex optimization, within-pair reindexing invariance, a
multi-bar exhaustive bottleneck oracle, lower-star bottleneck stability, and a
crop collision between distinct quotient orbits.

### 4. Run the frozen simulation

```bash
python scripts/run_simulation.py
```

Defaults are the frozen design: 250 replicates at each effect strength
\(0,0.35,0.70,1.00\), eight randomized blocks, 1,000 bytewise orbit-audit
trials, and seed 51907. The completed frozen run is stored under
`results/simulation`.

### 5. Run the RxRx1 confirmation experiment

Run this only after the image integrity manifest reports
`complete_crc_and_sha256_verified`:

```bash
python scripts/run_rxrx1_experiment.py
```

The representation and test routines are never given the generated site
transformations or their generating inputs. For each nuisance seed, the
program enforces an exact
clean-versus-contaminated equality gate for the quotient pixels and finite
Euler signature before writing inferential results.

### 6. Run the post-analysis robustness extensions

```bash
python scripts/run_expert_review_extensions.py
python scripts/build_extension_results_tex.py
```

The first command displays a percentage/ETA/failure progress bar. It verifies
the frozen primary statistic before computing any extension, then writes the
exact sensitivity and persistence audits under `results/extensions`. The
extension manifest explicitly records that the primary outcome had already
been accessed.

### 7. Build numerical TeX and compile the paper

```bash
python scripts/build_results_tex.py
python scripts/build_extension_results_tex.py
cd paper
pdflatex -interaction=nonstopmode -halt-on-error main.tex
bibtex main
pdflatex -interaction=nonstopmode -halt-on-error main.tex
pdflatex -interaction=nonstopmode -halt-on-error main.tex
```

Verify the complete current analysis-source manifest from the repository root:

```bash
sha256sum -c CURRENT_ANALYSIS_SOURCE_MANIFEST.sha256
```

The results builder refuses incomplete or unaudited inputs. It emits
`\resultsavailabletrue`, checks every results macro used by the paper, and
fails if any completed macro is missing or still contains `\pending`.

## Expected runtime and storage

Times depend on network throughput and CPU. The following ranges are practical
expectations for the container used for the reported analysis:

| Stage | Expected wall time | Notes |
|---|---:|---|
| Existing support-file verification | 1–3 seconds | Reads and hashes about 182 MB |
| Fresh support-file download | 1–5 minutes | About 51 MB compressed embeddings plus metadata |
| Confirmation PNG subset download | 30–90 minutes | 1,920 resumable range downloads; network-bound |
| Unit and audit tests | 3–10 seconds | No network |
| Frozen 250 × 4 simulation | about 12.5 minutes | Observed elapsed time: 746 seconds |
| Held-out RxRx1 analysis | about 25–45 minutes | 20 nuisance seeds; moment registration dominates |
| Post-analysis extension | under 1 minute | 252 verified progress steps in the supplied run |
| Results build and LaTeX compile | under 1 minute | Requires completed audited inputs |

The extracted support files occupy about 174 MB; their ZIPs add about 51 MB.
The selected PNG subset and generated figures/results require additional space
that depends on source compression. The analysis can transiently use roughly
one gigabyte of memory while clean and contaminated feature matrices coexist.

## Progress and failure monitoring

Every long-running script prints a progress bar with elapsed time, ETA, and
failure count, while atomically updating a JSON state file. For example:

```bash
python scripts/monitor_progress.py logs/progress_download.json
python scripts/monitor_progress.py logs/progress_simulation.json
python scripts/monitor_progress.py logs/progress_rxrx1_experiment.json
python scripts/monitor_progress.py logs/progress_expert_review_extensions.json
```

Support-file downloads also write per-object states such as
`logs/progress_support_files_embeddings.json`.

## Main outputs

```text
results/
├── extensions/
│   ├── rosenbaum_sensitivity.csv
│   ├── rosenbaum_summary.json
│   ├── persistence_stability.csv
│   ├── persistence_summary.json
│   └── expert_review_extension_audit.json
├── simulation/
│   ├── simulation_replicates.csv
│   ├── simulation_summary.csv
│   └── simulation_audit.json
└── rxrx1/
    ├── pair_seed_results.csv
    ├── acquisition_null_results.csv
    ├── acquisition_null_false_positive_summary.csv
    ├── clean_contaminated_equivalence.csv
    ├── approximate_action_stress.csv
    ├── hidden_nuisance_truth_NOT_ANALYSIS.csv
    └── experiment_summary.json
```

Figures are written to `paper/figures`; confirmatory numerical macros are
written to `paper/results.tex`, and audited post-analysis macros are written to
`paper/extension_results.tex`.

## Statistical interpretation

The exact claim is action-specific. For finite-support arrays, sitewise support
normalization followed by \(C_4\) canonicalization is invariant and maximal
under the declared product action. The full quotient-outcome law is therefore
the confirmatory target. The finite Euler vector is an invariant but
lower-dimensional secondary signature.

The off-grid rotations, support truncation, and noise experiment is explicitly
a robustness analysis outside the exact group action. Likewise, acquisition-only
rejection fractions across the fixed pair–seed grid are descriptive because
those tests share biological blocks. Their displayed Clopper–Pearson intervals
are computational binomial summaries, not independent-trial coverage claims.
Formal type-I calibration is assessed by the randomized sharp-null simulation.

The well—not a site, channel, cell, or pixel—is the experimental unit
throughout.

The invariant-endpoint RxRx1 \(p\)-values are finite-sample valid only
conditional on well-defined reagent versions, no cross-well interference,
swap-invariant block retention, and an explicit uniform-assignment premise:
conditional on the eligible wells, their complete potential-outcome schedule,
and pretreatment design information, the assignment vector must be uniform
over all within-block swaps. RxRx1 states
that non-control siRNA locations were randomized within experiment and plate,
but the public release does not include the original assignment log. Raw-pixel
and moment-registration paired-swap values are diagnostics and do not inherit
this causal validity under informative acquisition. The synthetic experiment
supplies a fully known randomization mechanism and independent Monte Carlo
replicates for implementation calibration.

The bounded-odds extension is a sensitivity analysis for hypothetical
nonuniformity of the reported paired assignment. It reconstructs pairs in
label-blind ascending-well-ID order, assumes conditionally independent
assignment bits, and does not establish that an unmeasured confounder existed.
The persistence extension concerns a separate invariant 16-by-16 diagnostic
vector, its own Gaussian kernel, and a continuous lower-star grayscale
filtration; it does not make a stability claim for the thresholded finite
Euler signature or change the primary full-image kernel.

## Repository map

```text
paper/                 manuscript, bibliography, generated figures and PDF
src/cqoi/              invariants, experiment, simulation and statistics code
scripts/               frozen runners, downloaders, monitoring and TeX builder
tests/                 dependency-free unit and audit tests
data/manifests/        selection, integrity records and pre-outcome amendments
results/               machine-readable simulation and RxRx1 outputs
logs/                  atomic progress states and run logs
rerun_evidence_2026-08-18/ current-source rerun summaries and timings
RERUN_AUDIT_2026-08-18.json machine-readable end-to-end comparison
```
