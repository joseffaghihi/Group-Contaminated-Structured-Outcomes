# Causal Inference for Group-Contaminated Structured Outcomes

Reproducibility code and reported outputs for **“Causal Inference for
Group-Contaminated Structured Outcomes: Quotient Identification and Exact
Randomization Inference”** by Usef Faghihi and Amir Saki.

- [Article PDF](paper/group_contaminated_structured_outcomes.pdf)
- [Reproducibility audit](docs/REPRODUCIBILITY_AUDIT.md)
- [Citation metadata](CITATION.cff)

This repository is arranged as a runnable research artifact. It contains the
analysis code, exact dependency versions, frozen design and integrity
manifests, machine-readable reported results, generated figures, tests, and the
final article PDF. Raw RxRx1 data are fetched from the official source and are
not redistributed here.

LaTeX/arXiv source files, duplicate release archives, runtime logs, and
intermediate build files are intentionally excluded. This repository
reproduces the analyses and numerical results; it is not a manuscript-build
repository.

## Quick validation

Use Python 3.12. From a clean clone:

```bash
python -m venv .venv
```

Activate the environment:

```bash
# macOS or Linux
source .venv/bin/activate

# Windows PowerShell
.\.venv\Scripts\Activate.ps1
```

Install the exact validated dependencies and run the offline test suite:

```bash
python -m pip install -r requirements.txt
python scripts/run_tests.py
```

The GitHub Actions workflow runs the same test command on every push and pull
request.

For a fast end-to-end smoke run of the simulation code without changing the
reported results:

```bash
python scripts/run_simulation.py \
  --replicates 2 \
  --invariance-audit-trials 10 \
  --output work/smoke/results \
  --figures work/smoke/figures \
  --progress work/smoke/progress.json
```

## Reproduce the reported analyses

Run all commands from the repository root.

### Frozen simulation

The simulation requires no external data:

```bash
python scripts/run_simulation.py
```

The frozen defaults are 250 replicates at each effect strength
`0, 0.35, 0.70, 1.00`, eight randomized blocks, 1,000 orbit-audit trials,
and seed 51907. Outputs are written to `results/simulation/` and
`results/figures/`.

### RxRx1 analysis

1. Download and verify the official metadata and embeddings:

   ```bash
   python scripts/fetch_rxrx1_support_files.py
   ```

2. Download and verify the frozen 1,920-image confirmation subset:

   ```bash
   python scripts/fetch_rxrx1_subset.py
   ```

3. Run the frozen confirmatory experiment:

   ```bash
   python scripts/run_rxrx1_experiment.py
   ```

4. Run the post-analysis sensitivity and persistence extensions:

   ```bash
   python scripts/run_expert_review_extensions.py
   ```

Downloaded files are stored under `data/raw/` and
`data/rxrx1_validation_subset/`. Both paths are ignored by Git. The analysis
will not start unless the frozen selection manifest, source-code hashes, and
all 1,920 image hashes pass their integrity gates.

To verify an existing support-data download without network access:

```bash
python scripts/fetch_rxrx1_support_files.py --verify-only
```

RxRx1 is distributed by Recursion under the terms linked from the
[official RxRx1 page](https://www.rxrx.ai/rxrx1). Users are responsible for
complying with those terms.

## Expected resources

Approximate times from the validated release environment:

| Stage | Typical time | Storage or notes |
|---|---:|---|
| Offline tests | 3–10 seconds | No network |
| Frozen simulation | about 12.5 minutes | CPU-bound |
| Support-file download | 1–5 minutes | About 51 MB compressed; about 174 MB extracted |
| Confirmation subset download | 30–90 minutes | 1,920 resumable PNG downloads |
| RxRx1 analysis | about 25–45 minutes | Roughly 1 GB peak memory |
| Robustness extensions | under 1 minute | Runs after the frozen experiment |

Network throughput and hardware will change these times.

## Reported outputs

```text
results/
├── extensions/        sensitivity and persistence results
├── figures/           publication figures in PDF and PNG formats
├── rxrx1/             confirmatory and diagnostic result tables
├── simulation/        frozen simulation tables and audits
└── audits/            release-level rerun summary
```

The principal machine-readable files are:

- `results/simulation/simulation_replicates.csv`
- `results/simulation/simulation_summary.csv`
- `results/rxrx1/pair_seed_results.csv`
- `results/rxrx1/experiment_summary.json`
- `results/extensions/rosenbaum_sensitivity.csv`
- `results/extensions/persistence_stability.csv`

Generated outputs contain audit hashes and status fields. Some audit JSON files
also preserve timestamps or paths from the original validated run; those
environment-specific fields are provenance, not analysis inputs.

## Frozen design and data boundaries

The discovery–confirmation split, selected treatment pairs, analysis
amendments, and integrity digests are stored in `data/manifests/`. Do not
overwrite the frozen `selection_manifest.json` when experimenting with a new
selection rule; pass an alternate `--manifest` path instead.

The well—not a site, channel, cell, or pixel—is the inferential unit. The
confirmatory representation is the explicit maximal invariant for the declared
two-site product action. Statistical interpretation and post-analysis
extensions are documented in:

- [Formula guide](docs/FORMULA_GUIDE.md)
- [Extension methods](docs/EXTENSION_METHODS.md)
- [Expert-suggestion audit](docs/EXPERT_SUGGESTION_AUDIT.md)

## Repository map

```text
.github/workflows/  automated offline test
src/cqoi/           analysis library
scripts/            download, validation, simulation, and experiment runners
tests/              dependency-free test functions and audit checks
data/manifests/     frozen design, amendments, and integrity records
results/            reported numerical outputs, figures, and audits
paper/              final article PDF only
docs/               scientific and reproducibility documentation
requirements.txt    exact Python dependency versions
CITATION.cff        GitHub citation metadata
```

The repository intentionally has no committed raw data, archive bundle,
arXiv-source directory, or `.tex` files.
