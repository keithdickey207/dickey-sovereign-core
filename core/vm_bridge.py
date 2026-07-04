#!/usr/bin/env python3
"""Bridge Dickey.OS Core → 04901 Sovereign VM telemetry bus."""

import os
import subprocess
import sys

GRID_ROOT = os.path.expanduser("~/projects/district_04901_grid")
EMITTER = os.path.join(GRID_ROOT, "tools", "telemetry_emitter.py")
FUSION_EMITTER = os.path.join(os.path.dirname(__file__), "fusion_telemetry.py")
TACTILE_EMITTER = os.path.join(os.path.dirname(__file__), "tactile_telemetry.py")
CORE_ROOT = os.path.dirname(os.path.dirname(__file__))
VENV_PYTHON = os.path.join(CORE_ROOT, ".venv", "bin", "python3")


def _python() -> str:
    return VENV_PYTHON if os.path.isfile(VENV_PYTHON) else sys.executable


def emit_telemetry(mode: str = "fusion", target: str = "127.0.0.1", port: int = 2368, hz: float = 10.0, json_path: str = None):
    """Launch UDP telemetry emitter toward ws-proxy."""
    if not os.path.isfile(EMITTER):
        print(f"[!] 04901 grid not found at {GRID_ROOT}")
        return None

    cmd = [_python(), EMITTER, "--mode", mode, "--target", target, "--port", str(port), "--hz", str(hz)]
    if json_path:
        cmd.extend(["--from-json", json_path])

    print(f"[*] Launching 04901 emitter: {' '.join(cmd)}")
    return subprocess.Popen(cmd)


def emit_fusion_telemetry(
    target: str = "127.0.0.1",
    port: int = 2368,
    hz: float = 10.0,
    Q: float = 15.0,
    volume: float = 0.1,
):
    """Stream D-³He torsatron physics state to 04901 VM."""
    if not os.path.isfile(FUSION_EMITTER):
        print(f"[!] Fusion telemetry missing: {FUSION_EMITTER}")
        return None
    cmd = [
        _python(), FUSION_EMITTER,
        "--target", target, "--port", str(port),
        "--hz", str(hz), "--Q", str(Q), "--volume", str(volume),
    ]
    print(f"[*] Launching fusion telemetry: {' '.join(cmd)}")
    return subprocess.Popen(cmd)


def emit_tactile_telemetry(
    target: str = "127.0.0.1",
    port: int = 2368,
    hz: float = 20.0,
):
    """Stream QCTB tactile pressure map to 04901 VM."""
    if not os.path.isfile(TACTILE_EMITTER):
        print(f"[!] Tactile telemetry missing: {TACTILE_EMITTER}")
        return None
    cmd = [
        _python(), TACTILE_EMITTER,
        "--target", target, "--port", str(port), "--hz", str(hz),
    ]
    print(f"[*] Launching tactile telemetry: {' '.join(cmd)}")
    return subprocess.Popen(cmd)


def grid_status():
    paths = {
        "grid_root": GRID_ROOT,
        "engine": os.path.join(GRID_ROOT, "src", "SovereignVMEngine.jsx"),
        "proxy": os.path.join(GRID_ROOT, "ws-proxy.js"),
        "emitter": EMITTER,
    }
    for name, path in paths.items():
        print(f"  {name}: {'OK' if os.path.exists(path) else 'MISSING'} ({path})")
    return paths