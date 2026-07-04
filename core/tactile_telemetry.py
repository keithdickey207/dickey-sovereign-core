#!/usr/bin/env python3
"""
QCTB tactile telemetry → 04901 Sovereign VM (16×16 pressure heatmap + slip state)
"""

import argparse
import json
import math
import random
import socket
import time

ANCHOR = {"lat": 44.5523, "lon": -69.6317, "district": "04901", "system": "QCTB-Tactile"}


def pressure_points(grid: list[list[float]], t: float) -> list[dict]:
    pts = []
    for r in range(16):
        for c in range(16):
            v = grid[r][c]
            x = (c - 8) * 12
            y = (r - 8) * 12
            z = v * 40
            pts.append({
                "x": x + math.sin(t + r * 0.3) * 2,
                "y": y + math.cos(t + c * 0.3) * 2,
                "z": z,
                "sig": min(1.0, max(0.05, v)),
                "type": "rf",
            })
    return pts


def simulate_grid(t: float, slip_event: bool) -> tuple[list[list[float]], dict]:
    grid = [[0.0] * 16 for _ in range(16)]
    cx, cy = 8 + int(math.sin(t * 0.7) * 3), 8 + int(math.cos(t * 0.5) * 3)
    for r in range(16):
        for c in range(16):
            d = math.hypot(r - cx, c - cy)
            grid[r][c] = max(0.0, 1.0 - d / 8.0) * (0.6 + 0.4 * random.random())
    if slip_event:
        for c in range(16):
            grid[15][c] = min(1.0, grid[15][c] + 0.5)

    piezo = [random.gauss(0, 0.3 if not slip_event else 1.2) for _ in range(32)]
    slip_prob = min(1.0, 0.1 + abs(sum(piezo)) / 20.0)
    return grid, {
        "phase": "slip" if slip_prob > 0.6 else "grip",
        "slip_probability": round(slip_prob, 3),
        "grip_force_delta": round((0.5 - slip_prob) * 0.2, 4),
        "taxel_rows": 16,
        "taxel_cols": 16,
        "piezo_window": 32,
        "wcet_target_ms": 10.0,
    }


def stream(target: str, port: int, hz: float):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    interval = 1.0 / max(hz, 1.0)
    t = 0.0
    print(f"[*] QCTB tactile telemetry → {target}:{port} @ {hz}Hz")
    try:
        while True:
            slip = (int(t * 10) % 17) == 0
            grid, tactile = simulate_grid(t, slip)
            payload = {
                "mode": "tactile",
                "anchor": ANCHOR,
                "t": round(t, 3),
                "tactile": tactile,
                "points": pressure_points(grid, t),
            }
            sock.sendto(json.dumps(payload).encode("utf-8"), (target, port))
            t += interval
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n[*] Tactile telemetry halted.")


def main():
    parser = argparse.ArgumentParser(description="QCTB tactile VM telemetry")
    parser.add_argument("--target", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=2368)
    parser.add_argument("--hz", type=float, default=20.0)
    args = parser.parse_args()
    stream(args.target, args.port, args.hz)


if __name__ == "__main__":
    main()
