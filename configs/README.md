# Configs

Top-level `configs/` is a compatibility pointer only.

Real run-specific configuration belongs inside an experiment package, for
example `experiments/example_experiment/configs/`. Reusable configuration
templates belong in `contracts/config_templates/`.

Do not add benchmark run configuration here unless a migration or compatibility
test explicitly requires it.
