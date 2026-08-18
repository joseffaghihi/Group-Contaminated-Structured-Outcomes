# arXiv preprint package

This package is independent of the Information and Inference authoring class and uses only standard TeX Live packages.

The author names and affiliations are already present. Empirical values are
loaded from the generated `results.tex` and `extension_results.tex` inputs;
`release_audit.tex` records the complete analysis-source manifest digest. The
simulation figure is the code-generated `simulation_power.pdf`.

Compile from this directory with:

```sh
pdflatex -interaction=nonstopmode -halt-on-error group_contaminated_structured_outcomes_arxiv.tex
pdflatex -interaction=nonstopmode -halt-on-error group_contaminated_structured_outcomes_arxiv.tex
pdflatex -interaction=nonstopmode -halt-on-error group_contaminated_structured_outcomes_arxiv.tex
```

Alternatively, run `latexmk -pdf` from this directory. The bibliography is
embedded in the TeX source, so no `.bib` file or journal class is required.
The upload archive intentionally excludes `.aux`, `.log`, `.out`,
`.synctex.gz` and other local build artifacts.
