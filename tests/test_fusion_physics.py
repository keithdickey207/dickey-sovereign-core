import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "core"))

from fusion_physics import (
    bosch_hale_d3he,
    run_full_audit,
    spitzer_resistivity,
    inductive_recovery,
    TorsatronConfig,
)


def test_bosch_hale_at_80kev():
    sv = bosch_hale_d3he(80.0)
    assert 1.0e-22 < sv < 2.0e-22


def test_spitzer_resistivity_positive():
    eta = spitzer_resistivity(20.0)
    assert 0 < eta < 1e-10


def test_flux_conserved_at_expansion():
    ind = inductive_recovery(TorsatronConfig())
    assert ind["flux_conserved"]


def test_audit_has_power_loops():
    r = run_full_audit()
    assert "power_loop_Q5" in r
    assert "power_loop_Q15" in r