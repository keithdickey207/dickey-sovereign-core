import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "core"))

from tactile_qctb import TactileConfig, run_full_audit, corrected_tactile_net_params, latency_audit


def test_wcet_budget_passes():
    report = latency_audit(TactileConfig())
    assert report["wcet_pass"]
    assert report["critical_path_total_ms"] == 10.0


def test_param_count_under_limit():
    p = corrected_tactile_net_params()
    assert p["under_150k_limit"]
    assert p["fusion_dim"] == 640


def test_full_audit_structure():
    r = run_full_audit()
    assert "topology_verification" in r
    assert "pennylane_ansatz" in r
    assert r["latency_budget"]["quantum_on_critical_path"] is False