# Current-source rerun audit

Status: **passed with non-numerical notes**. No core source file was edited, no scientific output changed, and `final_release` was not touched.

The archived source was read only at:

`/workspace/scratch/c78d01b81b62/audit_workspace/repro/causal_quotient_paper`

All executions used the isolated workcopy and output root:

`/workspace/scratch/c78d01b81b62/audit_workspace/agent_code_rerun`

The complete machine-readable record, including portable commands, exact command-record files, hashes, comparison rules, and paths, is `RERUN_AUDIT.json` in that directory.

## Bottom line

- All 45 unit tests pass.
- The full default simulation (250 replicates at each of four effects; 1,000 invariance audits; 2,000 tracked steps) completed with zero failures. Both numerical CSVs and the manuscript PNG are byte-identical to the archive.
- The official RxRx1 endpoints were accessible. The support CSVs matched the sealed hashes, and all 1,920 selected PNGs were downloaded and independently verified by CRC32 and SHA-256.
- The discovery-only selector reproduced all 10 ordered pairs, every score, and every plate map exactly.
- The full 20-seed RxRx1 experiment completed with zero failures. All six scientific CSVs and the PNG are byte-identical to the archive.
- The post-analysis Rosenbaum and persistence extension completed with zero failures. All four scientific output files are byte-identical to the archive.
- `paper/results.tex` regenerated from the fresh simulation and fresh RxRx1 outputs is byte-identical, SHA-256 `7dd075b2d5ce0eabc3515d950381278beb7d93426e31d3a71971c4f6a4a96be1`.
- No results-section number or experiment statement needs scientific modification.

## Environment

| Component | Observed | Pin |
|---|---:|---:|
| Python | 3.12.13, Clang 22.1.3 | not pinned |
| NumPy | 2.3.5 | 2.3.5 |
| pandas | 2.2.3 | 2.2.3 |
| SciPy | 1.17.0 | 1.17.0 |
| Matplotlib | 3.10.8 | 3.10.8 |
| Pillow | 12.3.0 | 12.2.0 |

Platform: `Linux-6.18.35-x86_64-with-glibc2.39`.

The Pillow patch-version deviation had no observed effect: all image-derived numerical outputs and the RxRx1 PNG are byte-identical, and the PDFs rasterize identically. A pinned downgrade trial was therefore not needed.

## Reproduction stages

| Stage | Runtime | Result | Archive comparison |
|---|---:|---|---|
| Unit tests | 1.863 s wall | 45/45 pass | no failures |
| Support-file fetch | 15.524 s progress time | metadata and embeddings sealed hashes pass | exact extracted-file hashes |
| Support verify-only | 0.194 s wall | 2/2 pass | frozen manifest `b6f350ca…` |
| Discovery-only selection | 3.762 s wall | 10 pairs | every scientific field exact |
| RxRx1 subset, interrupted 4-worker pass | 420.922 s | 436 atomic PNGs retained | no partial PNGs |
| RxRx1 subset, 16-worker resume | 489.934 s wall | 1,484 downloaded + 436 reused | all 1,920 records exact |
| Full default simulation | 254.753 s progress; 255.773 s observed wall | 2,000/2,000, zero failures | CSVs and PNG byte-identical |
| Fully captured simulation repeat | 447.828 s wall | 2,000/2,000, zero failures | same exact CSV/PNG hashes; normalized audit exact |
| Full RxRx1 confirmation | 228.573 s wall | 223/223, zero failures | all six CSVs and PNG byte-identical |
| Post-analysis extension | 2.649 s wall | 252/252, zero failures | all four scientific outputs byte-identical |
| Main TeX builder from fresh outputs | 0.311 s wall | completed | byte-identical |
| Extension TeX builder from fresh audit | 0.298 s wall | completed | numeric macros exact; one provenance hash changes |

## Integrity and hash comparisons

### Support data

- `metadata.csv`: 10,094,584 bytes, SHA-256 `799ed719d2be136db29fef6fcb7a51ceb94d1de9d43421a49b16409329a2f1b7`.
- `embeddings.csv`: 172,102,542 bytes, SHA-256 `e38f50b74c45682ec9ce7e6407b891c953c27217be5e39b187d289320395a192`.
- Frozen selection manifest: SHA-256 `b6f350ca96fb9e7a6271845dd6e432ed9dca556144a1a332d8f5af168642b968`.

The refreshed image-integrity manifest has a different whole-file hash because completion time, absolute path, and downloaded/reused counters differ. Its ordered `files` array is exactly identical to the archived manifest: 1,920 matching paths, sizes, CRC32 values, SHA-256 values, and order. Total bytes are 117,421,323 and the common aggregate digest is `ff14ffaecae84655f46b336bcacc2903ed1c7e83c641e00019fa4378cf8015eb`.

The raw support files and PNGs are external licensed data and must not be included in a redistributed manuscript artifact.

### Simulation

| Artifact | Rerun SHA-256 | Comparison |
|---|---|---|
| `simulation_replicates.csv` | `c8b0bc524063ef6725bcce37dcbff410c957a03edb500226288a32b9a6374049` | byte-identical |
| `simulation_summary.csv` | `409c66680379e04d8a34494aec901690c1f77eb73edaeb45d682999322a329f9` | byte-identical |
| `simulation_power.png` | `00f91301df4a4eda72b924343e3e60a99cf0905c4a655f0db5e88564352fe7de` | byte-identical |
| `simulation_power.pdf` | `675922074215dc6b48a1f18dd20613ae18d02f12618693e9cedeabd4042eecde` | container differs; 150-dpi raster byte-identical |

The rerun audit JSON differs from the archive only in creation time, paths, and host software strings. After removing `created_utc`, `outputs`, and `software`, it is structurally identical.

### RxRx1

| Artifact | SHA-256 | Comparison |
|---|---|---|
| `pair_seed_results.csv` | `7daf049b643a869f77ee5aaee3cdee15644ea7805c16a55052217b85f2420626` | byte-identical |
| `acquisition_null_results.csv` | `6a093b8768ff16263fe009b46d1333fd6fc52bb336ead5ddf1452c38e07ab632` | byte-identical |
| `acquisition_null_false_positive_summary.csv` | `6b4f67c5dd3ec449c13cefccc4db7f844230ddbf56cfae8f9cd210f691238427` | byte-identical |
| `approximate_action_stress.csv` | `bf300147876cb8635679fedb2eb833d76e63119f856fb25bd89c2b37a6a66ade` | byte-identical |
| `clean_contaminated_equivalence.csv` | `239d950bee3676e5d55bf2c6773720400191362134ef62ee59ccdd8cb0603a3e` | byte-identical |
| `hidden_nuisance_truth_NOT_ANALYSIS.csv` | `ae2cc341dc9e05fc2e8f48a38b7e1383fba63c278fa85d9153b0f2875e00fd75` | byte-identical |
| `rxrx1_mmd_by_method.png` | `d831d0b2a3395c9808ffc9c645d74d6679f1d56cebd9ed42988a850b556ebe20` | byte-identical |
| `rxrx1_mmd_by_method.pdf` | `abf2610336e53ff1454ea367dfe679fd1030d9e3fdf163cad284eb260d21936d` | container differs; 150-dpi raster byte-identical |

### Extensions

| Artifact | SHA-256 | Comparison |
|---|---|---|
| `rosenbaum_sensitivity.csv` | `c9b8ca543316e27086267a18a90e0ae6944567d3dae3407c1ddd2f8f9433b21a` | byte-identical |
| `persistence_stability.csv` | `9d4c872e188bc39a3fedffe2d946859aa963df3a4eb4011055a443aae5bcbb32` | byte-identical |
| `rosenbaum_summary.json` | `db0bcd9870b773d65db91bdf3cfd3a45a3da346162d017fbecb0abf7644e72c8` | byte-identical |
| `persistence_summary.json` | `4338c098b174c84b22799e4157d75ae3a70ff1f3ce13ff8a0c2885d3983a7e0f` | byte-identical |

The fresh `extension_results.tex` differs from the archived file in exactly one line: `RxExtensionAuditHash`. The fresh audit hash must change because the refreshed image-integrity manifest’s run metadata changed. All numerical macros are identical. If the fresh scientific outputs are built against the frozen audit, the TeX is byte-identical with SHA-256 `92d06e0e5a0049d5827be14080211fba232dc5248c4477289a76fb3f1935e37b`.

## Scientific results confirmed

- Simulation null rejection fractions: exact quotient 0.052, raw pixels 1.000, moment registration 0.056, finite Euler signature 0.040.
- At effect 1.0: exact quotient 0.992; raw, moment, and Euler 1.000.
- Primary RxRx1 seed 20260731: quotient statistic 0.003643781768319254 with exact p = 2/256 = 0.0078125; Euler p = 0.0078125; raw p = 0.0078125; moment p = 0.2109375.
- Nine secondary quotient contrasts: minimum raw p = 0.0078125, minimum Holm-adjusted p = 0.0703125, zero significant after Holm at 0.05.
- Exact clean/contaminated equivalence: all 20 pair-seed rows pass with zero quotient/Euler feature, statistic, and p-value discrepancies.
- Acquisition-only negative control, false positives out of 200: quotient 0, Euler 0, moment 0, raw 200.
- Rosenbaum sensitivity: critical Gamma = 2.1999953016638756.
- Persistence: all 32 exact and stability checks pass; maximum exact-action bottleneck distance 0.

## Scientific code review

- The paired randomization test exhaustively enumerates all 256 assignments. The exact tail fraction therefore does not need a Monte Carlo plus-one correction.
- Kernel bandwidth selection is label-blind and pooled.
- The simulated sharp null uses bytewise-identical unit-level potential outcomes before nuisance contamination.
- The exact endpoint applies finite-support cropping and sitewise canonicalization under rotations/translations, then aggregates the two sites at the well level.
- The well, not the site, is the scientific unit.
- The primary contrast is the prespecified sole primary test. The nine secondary contrasts form a separate Holm family. If all ten were treated as one family, the primary adjusted value would be 0.078125, but that is not the frozen plan.
- Only raw coordinates fail the exact acquisition-only control. Moment registration is 0/200 and should not be described as failing that control.
- Bootstrap quantiles and acquisition-null binomial intervals are transparently descriptive.
- Approximate rotations/cropping/noise are correctly reported as robustness diagnostics, not exact invariance claims.

No core statistical or implementation defect was found.

## Non-numerical findings

1. README command: from the repository root, `sha256sum -c data/manifests/selection_manifest.json.sha256` fails because the sidecar contains the basename only. Replace it with `(cd data/manifests && sha256sum -c selection_manifest.json.sha256)`. This has no numerical effect.
2. Downloader hygiene: a stale 30,408,704-byte `rxrx1-dl-embeddings.zip.part` remained after the valid final archive and extracted CSV passed all hashes. Verify-only ignored it correctly. Optional cleanup after successful verification would reduce confusion.
3. Source provenance: the archived independent simulation audit recorded earlier hashes for `simulation.py` and `invariants.py`. The new current-source audit closes this gap: the current code regenerates byte-identical CSVs and PNG.

## Evidence paths

- Machine audit: `/workspace/scratch/c78d01b81b62/audit_workspace/agent_code_rerun/RERUN_AUDIT.json`
- Current-source simulation reproduction audit used by `build_results_tex`: `/workspace/scratch/c78d01b81b62/audit_workspace/agent_code_rerun/current_simulation_reproduction_audit.json`
- Test log/timing: `tests_rerun.log`, `tests_rerun_timing.json`
- Selection log/timing: `selection_rerun.log`, `selection_rerun_timing.json`
- Support integrity: `rxrx1_support_integrity_rerun.json`, `rxrx1_support_integrity_verify_only.json`
- Subset log/timing: `subset_fetch_resume.log`, `subset_fetch_resume_timing.json`
- Simulation output: `full_simulation/`, `full_simulation_figures/`, `full_simulation_progress.json`
- Fully captured repeat: `full_simulation_captured.log`, `full_simulation_captured_timing.json`, `progress_full_simulation_captured.json`, `full_simulation_captured/`, `full_simulation_captured_figures/`
- RxRx1 log/timing/output: `rxrx1_rerun.log`, `rxrx1_rerun_timing.json`, `rxrx1_rerun/`, `rxrx1_rerun_figures/`
- Extension log/timing/output: `extensions_rerun.log`, `extensions_rerun_timing.json`, `extensions_rerun/`
- Fresh main TeX: `results_from_fully_rerun_outputs.tex`
- Fresh extension TeX: `extension_results_from_rerun.tex`

All relative evidence paths above are beneath `/workspace/scratch/c78d01b81b62/audit_workspace/agent_code_rerun`.
