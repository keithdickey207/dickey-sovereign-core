import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "core"))

from power_electronics import (
    PowerTrainConfig,
    run_full_audit,
    voltage_step_loss_reduction,
    institutional_chain_efficiency,
    sovereign_chain_efficiency,
)


def test_48v_i2r_reduction():
    s = voltage_step_loss_reduction(48.0, 12.0)
    assert abs(s["loss_reduction_pct"] - 93.75) < 0.01
    assert s["loss_multiplier"] == 16.0


def test_sovereign_beats_institutional():
    cfg = PowerTrainConfig()
    inst = institutional_chain_efficiency()
    sov = sovereign_chain_efficiency(cfg)
    assert sov["end_to_end_efficiency"] > inst["end_to_end_efficiency"]


def test_5mw_savings_positive():
    r = run_full_audit()
    sav = r["facility_savings_5MW"]
    assert sav["extra_chip_power_at_same_draw_MW"] > 0