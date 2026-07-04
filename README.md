# Dickey.OS Sovereign Core

**Master integration matrix for Waterville Software Development Services (WQSH / 04901)**  
**Lead Architect:** Keith Alan Dickey

Air-gapped command module integrating spatial intelligence, cyber threat analysis, fusion physics, grid-to-chip power modeling, quantum-classical tactile edge inference, and operational logistics — all routed through a local Ollama orchestration layer.

**Anchor:** `44.5520°N, 69.6317°W` (Waterville, ME 04901)


Feeds live physics and tactile streams into [District 04901 Grid](https://github.com/keithdickey207/District_04901_Grid) (React spatial C2) and complements [Aether Core](https://github.com/keithdickey207/aether) (USD-4 brain hub + Godot bridge).

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

```
dickey-sovereign-core  ──UDP :2368──►  telemetry_bridge.py / ws-proxy.js
                                              │
                                              ▼
                                    SovereignVMEngine.jsx (React VM)
```

```bash
# Terminal 1 — 04901 grid (Node or Python bridge)
cd ~/projects/district_04901_grid
npm run start:grid              # Node proxy + Vite
# bash start-grid-py.sh         # Python bridge + Vite (GNSS mesh)

# Terminal 2 — sovereign streams (from this repo)
cd ~/dickey-sovereign-core/core
python3 dickey_sovereign_core.py --fusion-stream --fusion-Q 15
python3 dickey_sovereign_core.py --tactile-stream
python3 dickey_sovereign_core.py --vm-emit --vm-mode fusion

# Terminal 3 (optional) — Pixel rover on mesh
cd ~/projects/district_04901_grid
python3 tools/pixel_rover.py --target 127.0.0.1 --device pixel_1
```

Open **http://127.0.0.1:5173** → **CONNECT WS** → `ws://127.0.0.1:8080`

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

## Sovereign Stack

| Project | Role |
|---------|------|
| **[Aether Core](https://github.com/keithdickey207/aether)** | Brain hub — USD-4 protocol, RF lab, medical, Godot 4 bridge |
| **[District 04901 Grid](https://github.com/keithdickey207/District_04901_Grid)** | Spatial C2 — React VM canvas, UDP/WS telemetry mesh |
| **dickey-sovereign-core** (this repo) | Fusion + tactile physics + LogisticsMatrix |
| **[waterville-ar](https://github.com/keithdickey207/waterville-ar)** | Godot city builder — 78 building footprints |
| **[04901-digital-twin](https://github.com/keithdickey207/04901-digital-twin)** | Godot digital twin — ram ingest lattice |
| **[04901-alchemical-chamber](https://github.com/keithdickey207/04901-alchemical-chamber)** | Godot Newton chymical lab node |
| **[chronosat](https://github.com/keithdickey207/chronosat)** | Orbital daemon + historical Landsat viewer |
| **[04901-sentinel](https://github.com/keithdickey207/04901-sentinel)** | NORAD tracker + bug bounty hunter |
| **[04901_Taxi_Dispatch](https://github.com/keithdickey207/04901_Taxi_Dispatch)** | Local-first taxi dispatch + fleet sim |
| **[document-fraud-detection-engine](https://github.com/keithdickey207/document-fraud-detection-engine)** | Sovereign document forensics |
| **[secure-self-healing-orchestrator](https://github.com/keithdickey207/secure-self-healing-orchestrator)** | Zero-trust LLM self-repair + FBI OSINT |
| **[newtons-alchemical-lab](https://github.com/keithdickey207/newtons-alchemical-lab)** | Historical chymistry CLI explorer |
| **[sovereign-sync](https://github.com/keithdickey207/sovereign-sync)** | Mesh glue — Syncthing, Tailscale, worktrees |
| **[dotfiles](https://github.com/keithdickey207/dotfiles)** | Multi-device bootstrap shell + env |
| **[goodperson](https://github.com/keithdickey207/goodperson)** | Good Person Protocol — daily practice CLI |

Sync mesh: Tailscale + Syncthing + git worktrees — see `~/SOVEREIGN_SYNC_QUICKSTART.md` and [sovereign-sync](https://github.com/keithdickey207/sovereign-sync).

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

MIT License — Copyright (c) 2026 Keith Dickey. See [LICENSE](LICENSE).
