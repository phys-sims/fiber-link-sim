from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any

import matplotlib
import numpy as np

matplotlib.use("Agg")
from matplotlib import pyplot as plt  # noqa: E402

from fiber_link_sim.artifacts import artifact_root_for_spec
from fiber_link_sim.data_models.spec_models import SimulationSpec
from fiber_link_sim.simulate import simulate
from fiber_link_sim.utils import bits_per_symbol, total_link_length_m


def main() -> None:
    args = _parse_args()
    spec_path = Path(args.spec)
    spec_payload = json.loads(spec_path.read_text())
    if args.n_symbols is not None:
        spec_payload["runtime"]["n_symbols"] = args.n_symbols
    spec_payload["outputs"]["artifact_level"] = args.artifact_level
    spec_payload["outputs"]["return_waveforms"] = True

    result, spec_model = _run_sim(spec_payload)
    run_id = args.run_id or result.provenance.spec_hash[:8]

    output_root = Path(args.output_dir) / run_id
    output_root.mkdir(parents=True, exist_ok=True)

    manifest = generate_story_assets(
        spec_model=spec_model,
        result=result.model_dump(),
        artifact_root=artifact_root_for_spec(result.provenance.spec_hash),
        output_root=output_root,
        image_format=args.format,
    )
    manifest_path = output_root / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True))

    if args.update_latest:
        latest_root = Path(args.output_dir) / "latest"
        if latest_root.exists():
            shutil.rmtree(latest_root)
        shutil.copytree(output_root, latest_root)

    if args.publish_dir:
        publish_root = Path(args.publish_dir) / run_id
        publish_root.mkdir(parents=True, exist_ok=True)
        publish_manifest = generate_story_assets(
            spec_model=spec_model,
            result=result.model_dump(),
            artifact_root=artifact_root_for_spec(result.provenance.spec_hash),
            output_root=publish_root,
            image_format="png",
        )
        publish_path = publish_root / "manifest.json"
        publish_path.write_text(json.dumps(publish_manifest, indent=2, sort_keys=True))
        print(f"Wrote publish assets to {publish_root}")

    print(f"Wrote story assets to {output_root}")


def generate_story_assets(
    *,
    spec_model: SimulationSpec,
    result: dict[str, Any],
    artifact_root: Path,
    output_root: Path,
    image_format: str = "svg",
) -> dict[str, Any]:
    stages: dict[str, list[dict[str, Any]]] = {}
    artifacts: list[dict[str, Any]] = []

    def add_artifact(stage: str, name: str, path: Path, kind: str) -> None:
        entry = {"stage": stage, "name": name, "path": str(path), "kind": kind}
        artifacts.append(entry)
        stages.setdefault(stage, []).append(entry)

    def save_json(stage: str, name: str, payload: dict[str, Any]) -> None:
        path = output_root / f"{name}.json"
        path.write_text(json.dumps(payload, indent=2, sort_keys=True))
        add_artifact(stage, name, path, "json")

    def load_npz(name: str) -> dict[str, np.ndarray]:
        path = artifact_root / f"{name}.npz"
        if not path.exists():
            return {}
        with np.load(path) as data:
            return {key: np.asarray(data[key]) for key in data.files}

    def save_fig(stage: str, name: str) -> None:
        path = output_root / f"{name}.{image_format}"
        plt.savefig(path, dpi=140, bbox_inches="tight")
        plt.close()
        add_artifact(stage, name, path, image_format)

    summary = result.get("summary") or {}
    latency = summary.get("latency_s") or {}
    errors = summary.get("errors") or {}

    # TxStage artifacts
    tx_psd = load_npz("tx_psd")
    if tx_psd:
        psd_db = _collapse_psd(tx_psd["psd_db"])
        plt.figure()
        plt.plot(tx_psd["freq_hz"], psd_db, lw=1.0)
        plt.xlabel("Frequency (Hz)")
        plt.ylabel("PSD (dB)")
        plt.title("Tx Spectrum")
        save_fig("tx", "tx_psd")

    tx_const = load_npz("tx_constellation")
    if tx_const:
        symbols = tx_const.get("symbols", np.array([]))
        plt.figure()
        plt.scatter(np.real(symbols), np.imag(symbols), s=6, alpha=0.7)
        plt.xlabel("I")
        plt.ylabel("Q")
        plt.title("Tx Constellation")
        plt.axis("equal")
        save_fig("tx", "tx_constellation")

    save_json(
        "tx",
        "tx_summary",
        {
            "payload_bits": spec_model.signal.frame.payload_bits,
            "symbol_rate_baud": spec_model.signal.symbol_rate_baud,
            "bits_per_symbol": bits_per_symbol(spec_model.signal),
        },
    )

    # ChannelStage artifacts
    channel_psd = load_npz("channel_psd")
    if channel_psd:
        psd_db = _collapse_psd(channel_psd["psd_db"])
        plt.figure()
        plt.plot(channel_psd["freq_hz"], psd_db, lw=1.0)
        plt.xlabel("Frequency (Hz)")
        plt.ylabel("PSD (dB)")
        plt.title("Channel Spectrum")
        save_fig("channel", "channel_psd")

    n_spans = _infer_n_spans(spec_model)
    osnr_db = summary.get("osnr_db")
    if osnr_db is not None:
        plt.figure()
        plt.plot(range(1, n_spans + 1), [osnr_db] * n_spans, marker="o")
        plt.xlabel("Span")
        plt.ylabel("OSNR (dB)")
        plt.title("OSNR per Span (flat assumption)")
        save_fig("channel", "channel_osnr")

    save_json("channel", "channel_summary", {"n_spans": n_spans, "osnr_db": osnr_db})

    # RxFrontEndStage artifacts
    rx_eye = load_npz("rx_eye").get("traces")
    if rx_eye is not None and rx_eye.size:
        plt.figure()
        for idx in range(min(rx_eye.shape[0], 32)):
            plt.plot(rx_eye[idx], color="tab:blue", alpha=0.3)
        plt.title("Rx Eye Diagram")
        plt.xlabel("Samples")
        plt.ylabel("Amplitude")
        save_fig("rx_frontend", "rx_eye")

    rx_samples = load_npz("rx_samples").get("data")
    if rx_samples is not None and rx_samples.size:
        samples = _first_column(rx_samples)
        plt.figure()
        plt.plot(np.real(samples[:512]), label="I", lw=0.8)
        if np.iscomplexobj(samples):
            plt.plot(np.imag(samples[:512]), label="Q", lw=0.8)
        plt.legend()
        plt.title("Rx Samples (time trace)")
        plt.xlabel("Sample")
        plt.ylabel("Amplitude")
        save_fig("rx_frontend", "rx_time_trace")

        plt.figure()
        plt.hist(np.real(samples), bins=50, alpha=0.7)
        plt.title("Rx ADC Histogram")
        plt.xlabel("Amplitude")
        plt.ylabel("Count")
        save_fig("rx_frontend", "rx_histogram")

    save_json(
        "rx_frontend",
        "rx_summary",
        {
            "adc_bits": spec_model.transceiver.rx.adc.bits,
            "sample_rate_hz": spec_model.transceiver.rx.adc.sample_rate_hz,
        },
    )

    # DSPStage artifacts
    dsp_const = load_npz("dsp_constellation").get("symbols")
    if dsp_const is not None and dsp_const.size:
        symbols = np.asarray(dsp_const)
        plt.figure()
        plt.scatter(np.real(symbols), np.imag(symbols), s=6, alpha=0.7)
        plt.xlabel("I")
        plt.ylabel("Q")
        plt.title("DSP Constellation (post-CPR)")
        plt.axis("equal")
        save_fig("dsp", "dsp_constellation")

    dsp_phase = load_npz("dsp_phase_error").get("radians")
    if dsp_phase is not None and dsp_phase.size:
        plt.figure()
        plt.plot(dsp_phase[:1024], lw=0.8)
        plt.xlabel("Symbol")
        plt.ylabel("Phase Error (rad)")
        plt.title("DSP Phase Error")
        save_fig("dsp", "dsp_phase_error")

    save_json(
        "dsp",
        "dsp_summary",
        {
            "evm_rms": summary.get("evm_rms"),
            "snr_db": summary.get("snr_db"),
            "dsp_chain": [block.model_dump() for block in spec_model.processing.dsp_chain],
        },
    )

    # FECStage artifacts
    plt.figure()
    plt.bar(["pre-FEC", "post-FEC"], [errors.get("pre_fec_ber"), errors.get("post_fec_ber")])
    plt.ylabel("BER")
    plt.title("FEC BER Comparison")
    save_fig("fec", "fec_ber")

    save_json(
        "fec",
        "fec_summary",
        {
            "enabled": spec_model.processing.fec.enabled,
            "scheme": spec_model.processing.fec.scheme,
            "code_rate": spec_model.processing.fec.code_rate,
            "pre_fec_ber": errors.get("pre_fec_ber"),
            "post_fec_ber": errors.get("post_fec_ber"),
        },
    )

    # MetricsStage artifacts
    if latency:
        plt.figure()
        names = [
            "propagation_s",
            "serialization_s",
            "dsp_group_delay_s",
            "fec_block_s",
            "queueing_s",
            "processing_s",
        ]
        values = [latency.get(name, 0.0) for name in names]
        plt.bar(names, values)
        plt.xticks(rotation=45, ha="right")
        plt.ylabel("Seconds")
        plt.title("Latency Budget")
        save_fig("metrics", "latency_budget")

    throughput = summary.get("throughput_bps") or {}
    plt.figure()
    plt.bar(
        ["raw", "net", "goodput"],
        [
            throughput.get("raw_line_rate"),
            throughput.get("net_after_fec"),
            throughput.get("goodput_est"),
        ],
    )
    plt.ylabel("bps")
    plt.title("Throughput Summary")
    save_fig("metrics", "throughput_summary")

    save_json(
        "metrics",
        "metrics_summary",
        {
            "latency_s": latency,
            "throughput_bps": throughput,
        },
    )

    return {
        "version": "v1",
        "run_id": output_root.name,
        "spec_hash": result.get("provenance", {}).get("spec_hash"),
        "seed": result.get("provenance", {}).get("seed"),
        "sim_version": result.get("provenance", {}).get("sim_version"),
        "artifacts": artifacts,
        "stages": stages,
        "summary": summary,
    }


def _run_sim(spec_payload: dict[str, Any]) -> tuple[Any, SimulationSpec]:
    spec_model = SimulationSpec.model_validate(spec_payload)
    result = simulate(spec_payload)
    if result.status != "success":
        raise RuntimeError(f"Simulation failed: {result.error}")
    return result, spec_model


def _infer_n_spans(spec_model: SimulationSpec) -> int:
    if spec_model.spans.mode == "from_path_segments":
        return len(spec_model.path.segments)
    total_m = total_link_length_m(spec_model.path)
    return max(1, int(np.ceil(total_m / spec_model.spans.span_length_m)))


def _collapse_psd(psd_db: np.ndarray) -> np.ndarray:
    psd_db = np.asarray(psd_db)
    if psd_db.ndim > 1:
        return np.mean(psd_db, axis=1)
    return psd_db


def _first_column(samples: np.ndarray) -> np.ndarray:
    samples = np.asarray(samples)
    if samples.ndim > 1:
        return samples[:, 0]
    return samples.reshape(-1)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate QPSK stage-by-stage story artifacts.")
    parser.add_argument(
        "--spec",
        default="src/fiber_link_sim/schema/examples/qpsk_longhaul_multispan.json",
        help="Path to SimulationSpec JSON.",
    )
    parser.add_argument(
        "--output-dir",
        default="docs/assets/qpsk_story",
        help="Output directory for story assets.",
    )
    parser.add_argument(
        "--run-id",
        default=None,
        help="Run identifier for output folder (defaults to spec hash prefix).",
    )
    parser.add_argument(
        "--n-symbols",
        type=int,
        default=None,
        help="Override runtime.n_symbols for faster generation.",
    )
    parser.add_argument(
        "--artifact-level",
        default="debug",
        choices=["none", "basic", "debug"],
        help="Artifact level for simulation outputs.",
    )
    parser.add_argument(
        "--format",
        default="svg",
        choices=["svg", "png"],
        help="Image format for local story assets.",
    )
    parser.add_argument(
        "--publish-dir",
        default=None,
        help="Optional directory to emit publish-ready PNGs (separate from local output).",
    )
    parser.add_argument(
        "--no-update-latest",
        action="store_false",
        dest="update_latest",
        help="Disable updating docs/assets/qpsk_story/latest.",
    )
    parser.set_defaults(update_latest=True)
    return parser.parse_args()


if __name__ == "__main__":
    main()
