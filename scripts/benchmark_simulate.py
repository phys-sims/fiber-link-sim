from __future__ import annotations

import argparse
import json
import os
import statistics
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from fiber_link_sim.simulate import simulate

DEFAULT_EXAMPLES = [
    "src/fiber_link_sim/schema/examples/ook_smoke.json",
    "src/fiber_link_sim/schema/examples/pam4_shorthaul.json",
    "src/fiber_link_sim/schema/examples/qpsk_longhaul_1span.json",
]

DEFAULT_PIPELINE_SPEC = "src/fiber_link_sim/schema/examples/qpsk_longhaul_1span.json"


@contextmanager
def _env_overrides(pairs: dict[str, str]) -> Iterator[None]:
    original: dict[str, str | None] = {key: os.environ.get(key) for key in pairs}
    try:
        for key, value in pairs.items():
            os.environ[key] = value
        yield
    finally:
        for key, previous in original.items():
            if previous is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = previous


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark simulation runtime across example specs.")
    parser.add_argument(
        "--mode",
        choices=["general", "phys-pipeline"],
        default="general",
        help="general: per-spec summary table; phys-pipeline: sequential vs DAG cache comparison.",
    )
    parser.add_argument(
        "--spec",
        action="append",
        default=[],
        help="Path to a spec JSON file. Can be passed multiple times.",
    )
    parser.add_argument("--repeat", type=int, default=3, help="Number of runs per benchmark cell.")
    parser.add_argument(
        "--warmup",
        type=int,
        default=1,
        help="Warmup runs per benchmark cell before recording timings.",
    )
    parser.add_argument(
        "--cache-root",
        type=Path,
        default=Path(".bench_phys_pipeline_cache"),
        help="Cache directory used by phys-pipeline DAG benchmarks.",
    )
    parser.add_argument(
        "--json",
        type=Path,
        default=None,
        help="Optional path for machine-readable benchmark output.",
    )
    return parser.parse_args()


def _p95(timings_s: list[float]) -> float:
    return sorted(timings_s)[max(0, int(0.95 * (len(timings_s) - 1)))]


def _run_repeated(spec_data: dict[str, Any], repeat: int, warmup: int) -> list[float]:
    for _ in range(warmup):
        warm = simulate(spec_data)
        if warm.status != "success":
            raise RuntimeError(f"warmup simulation failed: {warm.error}")

    timings_s: list[float] = []
    for _ in range(repeat):
        start = time.perf_counter()
        result = simulate(spec_data)
        elapsed = time.perf_counter() - start
        if result.status != "success":
            raise RuntimeError(f"simulation failed: {result.error}")
        timings_s.append(elapsed)
    return timings_s


def _summarize(*, label: str, spec_path: str, timings_s: list[float], repeat: int) -> dict[str, float | str | int]:
    return {
        "label": label,
        "spec": spec_path,
        "repeat": repeat,
        "min_s": min(timings_s),
        "mean_s": statistics.fmean(timings_s),
        "p95_s": _p95(timings_s),
        "max_s": max(timings_s),
    }


def _bench_general(spec_path: str, repeat: int, warmup: int) -> dict[str, float | str | int]:
    payload = json.loads(Path(spec_path).read_text())
    timings_s = _run_repeated(payload, repeat=repeat, warmup=warmup)
    return _summarize(label="general", spec_path=spec_path, timings_s=timings_s, repeat=repeat)


def _bench_phys_pipeline(
    spec_path: str,
    repeat: int,
    warmup: int,
    cache_root: Path,
) -> list[dict[str, float | str | int]]:
    payload = json.loads(Path(spec_path).read_text())
    rows: list[dict[str, float | str | int]] = []

    seq_timings = _run_repeated(payload, repeat=repeat, warmup=warmup)
    rows.append(_summarize(label="sequential", spec_path=spec_path, timings_s=seq_timings, repeat=repeat))

    dag_no_cache_env = {
        "FIBER_LINK_SIM_PIPELINE_EXECUTOR": "dag",
        "FIBER_LINK_SIM_PIPELINE_CACHE_BACKEND": "none",
        "FIBER_LINK_SIM_LOCAL_CACHE": "0",
    }
    with _env_overrides(dag_no_cache_env):
        dag_no_cache_timings = _run_repeated(payload, repeat=repeat, warmup=warmup)
    rows.append(
        _summarize(
            label="dag_no_cache",
            spec_path=spec_path,
            timings_s=dag_no_cache_timings,
            repeat=repeat,
        )
    )

    if cache_root.exists():
        for path in cache_root.glob("*"):
            if path.is_dir():
                for child in path.rglob("*"):
                    if child.is_file():
                        child.unlink()
                for child in sorted(path.rglob("*"), reverse=True):
                    if child.is_dir():
                        child.rmdir()
                path.rmdir()
            else:
                path.unlink()

    dag_cache_env = {
        "FIBER_LINK_SIM_PIPELINE_EXECUTOR": "dag",
        "FIBER_LINK_SIM_PIPELINE_CACHE_BACKEND": "disk",
        "FIBER_LINK_SIM_PIPELINE_CACHE_ROOT": str(cache_root),
        "FIBER_LINK_SIM_LOCAL_CACHE": "0",
    }
    with _env_overrides(dag_cache_env):
        cold_timings = _run_repeated(payload, repeat=repeat, warmup=0)
        warm_timings = _run_repeated(payload, repeat=repeat, warmup=max(1, warmup))

    rows.append(_summarize(label="dag_cache_cold", spec_path=spec_path, timings_s=cold_timings, repeat=repeat))
    rows.append(_summarize(label="dag_cache_warm", spec_path=spec_path, timings_s=warm_timings, repeat=repeat))
    return rows


def _print_rows(rows: list[dict[str, float | str | int]]) -> None:
    print("label,spec,repeat,min_s,mean_s,p95_s,max_s")
    for row in rows:
        print(
            f"{row['label']},{row['spec']},{row['repeat']},{row['min_s']:.6f},{row['mean_s']:.6f},{row['p95_s']:.6f},{row['max_s']:.6f}"
        )


def main() -> int:
    args = _parse_args()

    if args.mode == "general":
        specs = args.spec or DEFAULT_EXAMPLES
        rows = [_bench_general(spec_path, args.repeat, args.warmup) for spec_path in specs]
    else:
        specs = args.spec or [DEFAULT_PIPELINE_SPEC]
        rows = []
        for spec_path in specs:
            rows.extend(_bench_phys_pipeline(spec_path, args.repeat, args.warmup, args.cache_root))

    _print_rows(rows)

    if args.json is not None:
        args.json.write_text(json.dumps(rows, indent=2) + "\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
