# Current-source rerun evidence (2026-08-18)

This directory contains compact provenance files from the isolated current-code
rerun. Scientific CSVs and figures are not duplicated here when they reproduced
the archived files byte for byte; their exact comparisons and hashes are in
`../RERUN_AUDIT_2026-08-18.json`.

- `RERUN_AUDIT_DETAILED.json` and `.md`: the independent auditor's complete
  machine-readable and human-readable records, including portable commands,
  source hashes, comparison rules and evidence paths.
- `current_simulation_reproduction_audit.json`: full simulation settings,
  current loaded-source hashes, timings, output hashes and normalized audit
  comparison.
- `current_rxrx1_experiment_summary.json`: summary emitted by the fresh 20-seed
  real-image confirmation run.
- `current_extension_audit.json`: fresh bounded-odds and persistence extension
  audit.
- `rxrx1_subset_integrity.json` and sidecar: new hash-gated record for all 1,920
  reacquired official PNGs. Its file records are exactly equal to the archived
  record; its top-level hash differs because run metadata changed.
- `results_from_fully_rerun_outputs.tex`: core numerical TeX built only from the
  fresh simulation and RxRx1 outputs; it is byte-identical to `../paper/results.tex`.
- `extension_results_from_fully_rerun_outputs.tex`: extension TeX built from the
  fresh audit. Its numeric macros are identical to
  `../paper/extension_results.tex`; only the audit-JSON provenance hash differs.
- `*_timing.json`: captured commands, return codes, runtime and interpreter
  paths for the individual stages.

Absolute paths in these machine-emitted evidence files describe the isolated
audit workspace used for the rerun; they are provenance, not required runtime
locations. Portable reproduction commands are documented in `../README.md`.
