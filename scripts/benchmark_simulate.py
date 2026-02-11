from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path

from fiber_link_sim.simulate import simulate

DEFAULT_EXAMPLES = [
    "src/fiber_link_sim/schema/examples/ook_smoke.json",
    "src/fiber_link_sim/schema/examples/pam4_shorthaul.json",
    "src/fiber_link_sim/schema/examples/qpsk_longhaul_1span.json",
]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark simulation runtime across example specs.")
    parser.add_argument(
        "--spec",
        action="append",
        default=[],
        help="Path to a spec JSON file. Can be passed multiple times.",
    )
    parser.add_argument("--repeat", type=int, default=3, help="Number of runs per spec.")
    parser.add_argument(
        "--json",
        type=Path,
        default=None,
        help="Optional path for machine-readable benchmark output.",
    )
    return parser.parse_args()


def _bench_spec(spec_path: str, repeat: int) -> dict[str, float | str]:
    payload = json.loads(Path(spec_path).read_text())
    timings_s: list[float] = []

    for _ in range(repeat):
        start = time.perf_counter()
        result = simulate(payload)
        elapsed = time.perf_counter() - start
        if result.status != "success":
            raise RuntimeError(f"simulation failed for {spec_path}: {result.error}")
        timings_s.append(elapsed)

    return {
        "spec": spec_path,
        "repeat": repeat,
        "min_s": min(timings_s),
        "mean_s": statistics.fmean(timings_s),
        "p95_s": sorted(timings_s)[max(0, int(0.95 * (repeat - 1)))],
        "max_s": max(timings_s),
    }


def main() -> int:
    args = _parse_args()
    specs = args.spec or DEFAULT_EXAMPLES

    rows = [_bench_spec(spec_path, args.repeat) for spec_path in specs]

    print("spec,repeat,min_s,mean_s,p95_s,max_s")
    for row in rows:
        print(
            f"{row['spec']},{row['repeat']},{row['min_s']:.6f},{row['mean_s']:.6f},{row['p95_s']:.6f},{row['max_s']:.6f}"
        )

    if args.json is not None:
        args.json.write_text(json.dumps(rows, indent=2) + "\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
