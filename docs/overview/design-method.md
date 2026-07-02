# Design Method

The current top-level design has two parts:

- `Dataset Construction`
- `Benchmark Framework`

Dataset sources are fixed to four source routes:

- `public dataset`
- `benchmark research`
- `bioinformatics tool paper`
- `biomedical analysis paper`

Each later design discussion should follow the same progression:

```text
general batch workflow -> small-case demo test -> full-scale expansion
```

## Discussion Entry Points

- Data sources, download, organization, reference chain construction, review, and stratification belong under `docs/datasets/`.
- Benchmark conditions, output constraints, and experimental workflow belong under `docs/benchmark/`.
- Runner behavior, adapters, run directory layout, execution flow, and roadmap belong under `docs/workflow/`.
- Metrics, validators, scientific validity, and ranking belong under `docs/evaluation/`.
