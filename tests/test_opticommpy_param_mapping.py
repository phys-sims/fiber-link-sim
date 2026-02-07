from __future__ import annotations

import json
from pathlib import Path

from fiber_link_sim.adapters.opticommpy.param_builders import build_channel_params
from fiber_link_sim.data_models.spec_models import SimulationSpec

EXAMPLE_DIR = Path("src/fiber_link_sim/schema/examples")


def _load_example(name: str) -> dict:
    return json.loads((EXAMPLE_DIR / name).read_text())


def test_channel_params_disable_effects() -> None:
    spec_data = _load_example("qpsk_longhaul_manakov.json")
    spec_data["propagation"]["effects"] = {
        "dispersion": False,
        "nonlinearity": False,
        "ase": False,
        "pmd": False,
        "env_effects": False,
    }
    spec = SimulationSpec.model_validate(spec_data)
    param, layout = build_channel_params(spec, seed=123)

    assert param.D == 0.0
    assert param.gamma == 0.0
    assert param.amp == "ideal"
    assert param.NF == 0.0
    assert param.pmd_ps_sqrt_km == 0.0
    assert param.env_effects is False

    span_loss_db = spec.fiber.alpha_db_per_km * layout.span_length_km
    assert param.span_loss_db == span_loss_db
    assert param.amp_gain_db == min(span_loss_db, spec.spans.amplifier.max_gain_db or 0.0)


def test_channel_params_fixed_and_capped_gain() -> None:
    fixed_data = _load_example("qpsk_longhaul_manakov.json")
    fixed_data["spans"]["amplifier"]["mode"] = "fixed_gain"
    fixed_data["spans"]["amplifier"]["fixed_gain_db"] = 12.0
    fixed_data["spans"]["amplifier"].pop("max_gain_db", None)
    fixed_spec = SimulationSpec.model_validate(fixed_data)
    fixed_param, _ = build_channel_params(fixed_spec, seed=321)

    assert fixed_param.amp_gain_db == 12.0
    assert fixed_param.amp_mode == "fixed_gain"
    assert fixed_param.amp == "edfa"

    capped_data = _load_example("qpsk_longhaul_manakov.json")
    capped_data["spans"]["amplifier"]["max_gain_db"] = 5.0
    capped_spec = SimulationSpec.model_validate(capped_data)
    capped_param, _ = build_channel_params(capped_spec, seed=321)

    assert capped_param.amp_gain_db == 5.0
    assert capped_param.amp_mode == "auto_gain"
