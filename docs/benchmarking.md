# Benchmarking Guide

This repository provides two benchmarking views:

1. **General runtime benchmarking** across canonical example specs.
2. **Phys-pipeline execution benchmarking** that compares sequential execution with DAG executor modes
   (`dag_no_cache`, `dag_cache_cold`, `dag_cache_warm`).

## General benchmarking

Run default examples (OOK, PAM4, QPSK) with 3 measured runs per spec:

```bash
python scripts/benchmark_simulate.py --mode general --repeat 3
```

Custom specs + JSON output:

```bash
python scripts/benchmark_simulate.py \
  --mode general \
  --spec src/fiber_link_sim/schema/examples/ook_smoke.json \
  --spec src/fiber_link_sim/schema/examples/pam4_shorthaul.json \
  --repeat 5 \
  --warmup 1 \
  --json /tmp/fiber_link_sim_bench_general.json
```

## Phys-pipeline performance benchmarking

Benchmark the execution path choices for the same spec:

- `sequential`: baseline `SequentialPipeline`
- `dag_no_cache`: `DagExecutor` with cache disabled
- `dag_cache_cold`: first DAG runs with disk cache enabled
- `dag_cache_warm`: repeated DAG runs after cache warmup

```bash
python scripts/benchmark_simulate.py \
  --mode phys-pipeline \
  --spec src/fiber_link_sim/schema/examples/qpsk_longhaul_1span.json \
  --repeat 3 \
  --warmup 1 \
  --cache-root /tmp/fiber_link_sim_phys_pipeline_cache \
  --json /tmp/fiber_link_sim_bench_phys_pipeline.json
```

## Output schema

The script prints CSV rows and can optionally emit JSON. Each row includes:

- `label`
- `spec`
- `repeat`
- `min_s`
- `mean_s`
- `p95_s`
- `max_s`

Use the same host/load conditions when comparing historical runs.
