from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from fiber_link_sim.simulate import simulate


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a fiber link simulation from a spec file.",
    )
    parser.add_argument(
        "spec",
        type=Path,
        help="Path to a SimulationSpec JSON file.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Optional path to write the SimulationResult JSON output.",
    )
    return parser.parse_args(argv)


def _write_result(payload: dict[str, Any], output: Path | None) -> None:
    if output is None:
        json.dump(payload, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
        return

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    result = simulate(args.spec)
    _write_result(result.model_dump(mode="json"), args.output)
    return 0 if result.status == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
