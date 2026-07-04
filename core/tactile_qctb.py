#!/usr/bin/env python3
"""
Quantum-Classical Tactile Bridge (QCTB) — Architecture Audit Engine
Classical Inference Core (CIC) + async Quantum-Classical Interface (QCI)
WQSH / Dickey.OS Sovereign Edge Robotics
"""

import argparse
import json
import math
from dataclasses import dataclass, asdict


@dataclass
class TactileConfig:
    taxel_rows: int = 16
    taxel_cols: int = 16
    capacitive_hz: float = 100.0
    piezo_hz: float = 1000.0
    piezo_window: int = 32
    wcet_target_ms: float = 10.0
    trt_budget_ms: float = 1.20
    actuation_budget_ms: float = 2.0
    quantum_update_ms: float = 50.0
    quantum_n_qubits: int = 6
    quantum_cycle_interval: int = 50
    control_loop_hz: float = 100.0


LATENCY_BUDGET = [
    ("Data ingestion & normalization", "MCU → Edge CPU", 1.50, "Lock-free ring buffer, vectorized C++"),
    ("Zero-copy H2D pointer setup", "Jetson CPU", 0.15, "cudaHostAllocMapped + cudaHostGetDevicePointer"),
    ("TensorRT CIC execution", "Orin Tensor Cores", 1.20, "FP16 fused kernels, batch=1"),
    ("D2H + post-process", "Jetson CPU", 0.15, "Output thresholding on pinned host"),
    ("Actuation bus serialization", "Edge CPU → CAN FD/RS-485", 2.00, ">1 Mbps servo bus"),
    ("System margin / jitter", "—", 5.00, "OS scheduling safety"),
]


def conv2d_output_size(h: int, w: int, k: int, s: int, p: int) -> tuple[int, int]:
    oh = (h + 2 * p - k) // s + 1
    ow = (w + 2 * p - k) // s + 1
    return oh, ow


def conv1d_output_size(l: int, k: int, s: int, p: int) -> int:
    return (l + 2 * p - k) // s + 1


def conv2d_params(c_in: int, c_out: int, k: int, bias: bool = True) -> int:
    n = c_in * c_out * k * k
    return n + (c_out if bias else 0)


def conv1d_params(c_in: int, c_out: int, k: int, bias: bool = True) -> int:
    n = c_in * c_out * k
    return n + (c_out if bias else 0)


def linear_params(f_in: int, f_out: int, bias: bool = True) -> int:
    return f_in * f_out + (f_out if bias else 0)


def audit_spec_topology(cfg: TactileConfig) -> dict:
    """Verify documented Tactile-Net dimensions vs actual conv arithmetic."""
    h, w = cfg.taxel_rows, cfg.taxel_cols
    # Spec: two conv2d layers as documented
    h1, w1 = conv2d_output_size(h, w, 3, 1, 1)
    h2, w2 = conv2d_output_size(h1, w1, 3, 2, 1)
    spatial_flat_spec = 512
    spatial_flat_actual = 32 * h2 * w2

    t = cfg.piezo_window
    t1 = conv1d_output_size(t, 3, 1, 1)
    t2 = conv1d_output_size(t1, 3, 2, 1)
    temporal_flat_spec = 128
    temporal_flat_actual = 16 * t2

    return {
        "spatial_path": {
            "input_shape": [1, 1, h, w],
            "after_conv1": [1, 16, h1, w1],
            "after_conv2_stride2": [1, 32, h2, w2],
            "flatten_spec": spatial_flat_spec,
            "flatten_actual": spatial_flat_actual,
            "spec_matches": spatial_flat_spec == spatial_flat_actual,
            "fix": "Add AdaptiveAvgPool2d(4×4) or second stride-2 conv to reach 512-dim" if spatial_flat_spec != spatial_flat_actual else None,
        },
        "temporal_path": {
            "input_shape": [1, 1, t],
            "after_conv1": [1, 8, t1],
            "after_conv2_stride2": [1, 16, t2],
            "flatten_spec": temporal_flat_spec,
            "flatten_actual": temporal_flat_actual,
            "spec_matches": temporal_flat_spec == temporal_flat_actual,
            "fix": "Add second Conv1d stride-2 or pool to 8 samples → 16×8=128" if temporal_flat_spec != temporal_flat_actual else None,
        },
        "fusion_concat_spec": 640,
        "fusion_concat_actual": spatial_flat_actual + temporal_flat_actual,
    }


def corrected_tactile_net_params() -> dict:
    """
    Corrected topology matching spec intent: spatial 512 + temporal 128 = 640.
    Spatial: 16×16 → conv → conv s2 → 8×8 → avgpool 4×4 → 32×16=512
    Temporal: 32 → conv → conv s2 → 16 → conv s2 → 8 → 16×8=128
    """
    layers = []
    total = 0

    def add(name, n):
        nonlocal total
        total += n
        layers.append({"layer": name, "params": n})

    add("conv2d_1 (1→16, 3×3)", conv2d_params(1, 16, 3))
    add("conv2d_2 (16→32, 3×3, s2)", conv2d_params(16, 32, 3))
    add("conv1d_1 (1→8, 3)", conv1d_params(1, 8, 3))
    add("conv1d_2 (8→16, 3, s2)", conv1d_params(8, 16, 3))
    add("conv1d_3 (16→16, 3, s2)", conv1d_params(16, 16, 3))
    add("linear_640→64", linear_params(640, 64))
    add("linear_64→2", linear_params(64, 2))

    return {
        "layers": layers,
        "total_params": total,
        "under_150k_limit": total < 150_000,
        "spatial_flatten": 512,
        "temporal_flatten": 128,
        "fusion_dim": 640,
        "outputs": ["slip_probability (sigmoid)", "grip_force_delta (raw)"],
        "corrections_applied": [
            "AdaptiveAvgPool2d(4×4) after spatial convs for 512-dim flatten",
            "Third Conv1d stride-2 on temporal branch for 128-dim flatten",
        ],
    }


def latency_audit(cfg: TactileConfig) -> dict:
    stages = [{"stage": s, "hardware": h, "budget_ms": b, "mechanism": m} for s, h, b, m in LATENCY_BUDGET]
    critical_sum = sum(s["budget_ms"] for s in stages)
    loop_period_ms = 1000.0 / cfg.control_loop_hz
    return {
        "critical_path_stages": stages,
        "critical_path_total_ms": critical_sum,
        "wcet_target_ms": cfg.wcet_target_ms,
        "wcet_pass": critical_sum <= cfg.wcet_target_ms,
        "control_loop_hz": cfg.control_loop_hz,
        "loop_period_ms": loop_period_ms,
        "inference_fits_in_loop": cfg.trt_budget_ms < loop_period_ms,
        "quantum_async_ms": cfg.quantum_update_ms,
        "quantum_on_critical_path": False,
        "note": "Quantum QCI runs every N cycles on secondary stream — never blocks WCET",
    }


def qci_encoding(feature_dim: int = 64, n_qubits: int = 6) -> dict:
    """Classic → Quantum elevation math for post-fusion feature vectors."""
    # Amplitude encoding: need 2^n >= dim for exact amplitude encoding
    amp_qubits_needed = math.ceil(math.log2(max(feature_dim, 2)))
    # Angle encoding: n angles per qubit via RX/RY/RZ layers
    angles_per_layer = n_qubits * 3
    return {
        "feature_dim": feature_dim,
        "n_qubits": n_qubits,
        "amplitude_encoding_qubits_required": amp_qubits_needed,
        "angle_encoding": f"{feature_dim} features → pad/slice to {n_qubits * 3} rotation angles (RX/RY/RZ per qubit)",
        "normalization": "L2-normalize feature vector before encoding (valid quantum state)",
        "piezoresistive_mapping": "ΔR/R₀ → RY(θ) where θ = π × clamp(ΔR/R₀, 0, 1)",
        "capacitive_mapping": "ΔC/C₀ → amplitude α = sqrt(clamp(ΔC/C₀, 0, 1))",
        "collapse_outputs": ["fusion_weight_delta[64]", "slip_threshold_adjust", "pid_gain_kp_delta"],
    }


def pennylane_vqc_ansatz(n_qubits: int = 6, n_layers: int = 2) -> str:
    """PennyLane VQC for async grip-policy optimization (export for edge build)."""
    return f'''import pennylane as qml
import numpy as np

n_qubits = {n_qubits}
n_layers = {n_layers}
dev = qml.device("default.qubit", wires=n_qubits)

@qml.qnode(dev, interface="autograd")
def grip_vqc(features, weights):
    """
    Classic → Quantum: features = post-ReLU 64-dim fusion vector (normalized).
    Weights = variational parameters updated async every 50–200 ms.
    """
    # Amplitude/angle hybrid encoding
    for i in range(min(len(features), n_qubits)):
        qml.RY(features[i] * np.pi, wires=i)

    # Variational layers
    for layer in range(n_layers):
        for i in range(n_qubits):
            qml.RX(weights[layer, i, 0], wires=i)
            qml.RY(weights[layer, i, 1], wires=i)
            qml.RZ(weights[layer, i, 2], wires=i)
        # Entanglement ring
        for i in range(n_qubits - 1):
            qml.CNOT(wires=[i, i + 1])
        qml.CNOT(wires=[n_qubits - 1, 0])

    # Quantum → Classic: expectation values drive fusion weight deltas
    return [qml.expval(qml.PauliZ(i)) for i in range(min(4, n_qubits))]

def grip_cost(slip_prob, force_delta, expectations, target_slip=0.1):
    """Multi-objective: minimize slip, penalize crush (high force_delta)."""
    w_slip = expectations[0]
    w_force = expectations[1]
    return (slip_prob - target_slip) ** 2 * (1 + w_slip) + max(0, force_delta) ** 2 * (1 + w_force)
'''


def numpy_vqc_demo(features: list[float], n_qubits: int = 4) -> dict:
    """Minimal statevector demo without PennyLane dependency."""
    n = min(n_qubits, len(features))
    # Encode as rotation angles → pseudo expectation (cosine projection)
    expectations = [math.cos(features[i] * math.pi) for i in range(n)]
    slip_threshold_adj = 0.5 + 0.1 * expectations[0]
    kp_delta = 0.05 * expectations[1] if len(expectations) > 1 else 0.0
    return {
        "encoded_qubits": n,
        "expectations_Z": [round(e, 4) for e in expectations],
        "collapse_injection": {
            "slip_threshold": round(slip_threshold_adj, 4),
            "pid_kp_delta": round(kp_delta, 4),
        },
    }


def gelsight_branch_spec() -> dict:
    """Third input branch for optical tactile (async, higher latency path)."""
    return {
        "tensor_shape": [1, 3, 64, 64],
        "source": "GelSight dome marker deformation → classical CV pipeline",
        "latency_budget_ms": 8.0,
        "on_critical_path": False,
        "fusion_point": "Feature vector [128] concatenated at QCI layer, not CIC WCET path",
        "qci_use": "Quantum kernel embedding of 3D contact mesh descriptors",
        "integration": "Separate CUDA stream; updates texture class prior every 100 ms",
    }


def transduction_layer_audit() -> list[dict]:
    return [
        {
            "method": "Piezoresistive (FSR)",
            "strength": "Absolute grip force",
            "weakness": "Low spatial resolution",
            "qctb_encoding": "ΔR → RY rotation angle",
            "critical_path": True,
        },
        {
            "method": "Capacitive array",
            "strength": "Localized pressure map C ∝ 1/d",
            "weakness": "Matrix scan latency at high density",
            "qctb_encoding": "ΔC vector → amplitude encoding",
            "critical_path": True,
        },
        {
            "method": "Piezoelectric",
            "strength": "Dynamic slip/texture (1 kHz events)",
            "weakness": "No static force",
            "qctb_encoding": "Event triggers + stochastic VQC branch",
            "critical_path": True,
        },
        {
            "method": "Optical (GelSight)",
            "strength": "Rich 3D contact mesh",
            "weakness": "Higher compute cost",
            "qctb_encoding": "CV features → quantum kernel SVM",
            "critical_path": False,
        },
    ]


def run_full_audit(cfg: TactileConfig = None) -> dict:
    cfg = cfg or TactileConfig()
    topo = audit_spec_topology(cfg)
    params = corrected_tactile_net_params()
    lat = latency_audit(cfg)
    return {
        "config": asdict(cfg),
        "architecture": "QCTB v2 — Classical Inference Core + async QCI",
        "transduction": transduction_layer_audit(),
        "topology_verification": topo,
        "corrected_tactile_net": params,
        "latency_budget": lat,
        "qci_encoding": qci_encoding(64, cfg.quantum_n_qubits),
        "gelsight_branch": gelsight_branch_spec(),
        "pennylane_ansatz": pennylane_vqc_ansatz(cfg.quantum_n_qubits),
        "vqc_demo": numpy_vqc_demo([0.2, 0.5, 0.8, 0.1], min(4, cfg.quantum_n_qubits)),
        "cpp_hook": {
            "class": "TactileInferenceLoop",
            "quantum_member": "QuantumOptimizer q_optimizer",
            "async_trigger": f"cycle_count % {cfg.quantum_cycle_interval} == 0",
            "injection_targets": ["Linear(640→64) scaling", "slip_threshold", "PID Kp"],
            "zero_copy_preserved": True,
        },
    }


def print_audit(report: dict):
    print("\n" + "=" * 68)
    print("  QUANTUM-CLASSICAL TACTILE BRIDGE (QCTB) — ARCHITECTURE AUDIT")
    print("=" * 68)

    topo = report["topology_verification"]
    sp = topo["spatial_path"]
    tp = topo["temporal_path"]
    print("\n[1] TACTILE-NET TOPOLOGY VERIFICATION")
    print(f"    Spatial flatten: spec={sp['flatten_spec']} actual={sp['flatten_actual']} {'✓' if sp['spec_matches'] else '✗ FIX NEEDED'}")
    if sp.get("fix"):
        print(f"      → {sp['fix']}")
    print(f"    Temporal flatten: spec={tp['flatten_spec']} actual={tp['flatten_actual']} {'✓' if tp['spec_matches'] else '✗ FIX NEEDED'}")
    if tp.get("fix"):
        print(f"      → {tp['fix']}")

    p = report["corrected_tactile_net"]
    print(f"\n[2] CORRECTED MODEL (spec intent)")
    print(f"    Parameters: {p['total_params']:,} ({'✓' if p['under_150k_limit'] else '✗'} <150k limit)")
    print(f"    Fusion: {p['fusion_dim']}-dim → 64 → 2 heads")

    lat = report["latency_budget"]
    print(f"\n[3] WCET LATENCY BUDGET")
    for s in lat["critical_path_stages"]:
        print(f"    {s['budget_ms']:5.2f} ms  {s['stage']}")
    print(f"    TOTAL: {lat['critical_path_total_ms']:.2f} ms / {lat['wcet_target_ms']:.2f} ms target {'✓' if lat['wcet_pass'] else '✗'}")
    print(f"    Quantum path: async {report['config']['quantum_update_ms']:.0f} ms — NOT on critical path")

    qci = report["qci_encoding"]
    print(f"\n[4] QCI ENCODING ({qci['n_qubits']} qubits)")
    print(f"    {qci['angle_encoding']}")
    demo = report["vqc_demo"]
    print(f"    Demo collapse: slip_threshold={demo['collapse_injection']['slip_threshold']}, Kp_delta={demo['collapse_injection']['pid_kp_delta']}")

    print(f"\n[5] GELSIGHT BRANCH (3rd input, off critical path)")
    g = report["gelsight_branch"]
    print(f"    {g['tensor_shape']} @ {g['latency_budget_ms']} ms budget → QCI fusion only")

    print(f"\n[6] C++ INTEGRATION HOOK")
    c = report["cpp_hook"]
    print(f"    {c['class']} + {c['quantum_member']}")
    print(f"    Trigger: {c['async_trigger']} → inject to {', '.join(c['injection_targets'])}")

    print("=" * 68 + "\n")


def main():
    parser = argparse.ArgumentParser(description="QCTB tactile architecture audit")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--export-ansatz", metavar="FILE", help="Write PennyLane VQC to file")
    args = parser.parse_args()

    report = run_full_audit()
    if args.export_ansatz:
        with open(args.export_ansatz, "w", encoding="utf-8") as fh:
            fh.write(report["pennylane_ansatz"])
        print(f"[+] PennyLane ansatz: {args.export_ansatz}")

    if args.json:
        # pennylane_ansatz is large string — still valid JSON
        print(json.dumps(report, indent=2))
    else:
        print_audit(report)


if __name__ == "__main__":
    main()
