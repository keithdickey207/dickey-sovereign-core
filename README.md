# Dickey.OS Sovereign Core

**Master integration matrix for Waterville Software Development Services (WQSH / 04901)**  
**Lead Architect:** Keith Alan Dickey

Air-gapped command module integrating spatial intelligence, cyber threat analysis, fusion physics, grid-to-chip power modeling, quantum-classical tactile edge inference, and operational logistics — all routed through a local Ollama orchestration layer.

## Doctrine

- **Local-first:** No cloud APIs for telemetry, inference, or pipeline routing
- **Sovereign execution:** Ollama + internal mesh (Tailscale) only
- **Operational resilience:** Runs on edge nodes, homelab accelerators, and Synology-backed storage

## Subsystems

| Subsystem | Module | CLI |
|-----------|--------|-----|
| Digital Twin (Godot/PostGIS) | `core/digital_twin_ingest.py` | `--twin-ingest FILE` |
| Galactic Navigation (SNN) | `core/galactic_nav.py` | `--nav-demo` |
| Threat Intel (CVSS) | `core/threat_intel_cvss.py` | `--threat-score FILE` |
| Logistics (04901) | `core/logistics_matrix.py` | `--logistics-status` |
| D-³He Fusion Physics | `core/fusion_physics.py` | `--fusion-audit` |
| Grid-to-Chip Power | `core/power_electronics.py` | `--power-audit` |
| QCTB Tactile Edge | `core/tactile_qctb.py` | `--tactile-audit` |
| Sovereign CTI | `cti/pipeline.py` | `--cti-status` |
| 04901 VM Bridge | `core/vm_bridge.py` | `--vm-status` |

## Installation

```bash
git clone git@github.com:keithdickey207/dickey-sovereign-core.git
cd dickey-sovereign-core

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Optional: PyTorch + ONNX export for Tactile-Net
pip install -r requirements-ml.txt

# Requires local Ollama daemon for --analyze / --cti-correlate
systemctl status ollama
```

## Quick Start

```bash
cd core
python3 dickey_sovereign_core.py --status
```

### Physics & Power Audits

```bash
python3 dickey_sovereign_core.py --fusion-audit
python3 dickey_sovereign_core.py --power-audit
python3 dickey_sovereign_core.py --tactile-audit
```

### Live VM Telemetry (with [District 04901 Grid](https://github.com/keithdickey207/District_04901_Grid))

```bash
# Terminal 1 — 04901 grid
cd ~/projects/district_04901_grid && npm run start:grid

# Terminal 2 — pick a stream
python3 dickey_sovereign_core.py --fusion-stream --fusion-Q 15
python3 dickey_sovereign_core.py --tactile-stream
python3 dickey_sovereign_core.py --vm-emit --vm-mode fusion
```

### CTI Pipeline

```bash
python3 dickey_sovereign_core.py --cti-status
python3 dickey_sovereign_core.py --cti-rag
# Place GeoLite2-ASN.mmdb in data/ for ASN risk-flagging
```

### Export Artifacts

```bash
python3 dickey_sovereign_core.py --fusion-export ../data/fusion_audit.json
python3 dickey_sovereign_core.py --power-export ../data/power_audit.json
python3 dickey_sovereign_core.py --tactile-export ../data/qctb_audit.json
python3 dickey_sovereign_core.py --tactile-ansatz ../data/grip_vqc.py
```

## QCTB Tactile Stack

| Layer | Path | Notes |
|-------|------|-------|
| Architecture audit | `core/tactile_qctb.py` | WCET budget, topology verification |
| PyTorch model | `core/tactile_net.py` | 47k params, 16×16 + 32-sample fusion |
| ONNX export | `core/build_tactile_onnx.py` | TensorRT input for Jetson Orin |
| C++ CIC skeleton | `tactile/` | Zero-copy + quantum hook stub |
| VM telemetry | `core/tactile_telemetry.py` | 16×16 pressure heatmap → UDP |

```bash
# Build C++ demo (stub, no CUDA)
cd tactile && cmake -B build && cmake --build build && ./build/tactile_demo

# Export ONNX (requires torch)
python3 core/build_tactile_onnx.py
```

## Tests

```bash
pip install pytest
pytest tests/ -v
```

## Repository Layout

```
dickey-sovereign-core/
├── core/           # Master daemon + subsystem modules
├── cti/            # Passive CTI pipeline (CertStream → SQLite → RAG)
├── tactile/        # C++ Classical Inference Core skeleton
├── models/         # ONNX / TensorRT artifacts (gitignored, regenerate)
├── data/           # SQLite, audit exports (db gitignored)
├── tests/          # pytest suite
└── .github/        # CI workflow
```

## License

MIT License — Copyright (c) 2026 Waterville Software Development Services. See [LICENSE](LICENSE).