#!/usr/bin/env python3
"""
D-³He Torsatron — Live telemetry stream for 04901 Sovereign VM
UDP JSON frames → ws-proxy.js → React HUD
"""

import argparse
import json
import math
import socket
import sys
import time

from fusion_physics import (
    TorsatronConfig,
    bosch_hale_d3he,
    inductive_recovery,
    pulse_energy_balance,
    run_full_audit,
    spitzer_equipartition_s,
)

# Audit-corrected burn window: intermediate compression, not peak n
OPTIMAL_BURN_N = 4.0e21
PEAK_N = 6.0e22

PHASES = ("compression", "burn", "expansion", "recovery")
ANCHOR = {"lat": 44.5523, "lon": -69.6317, "district": "04901", "system": "D3He-Torsatron"}


def torsatron_visual_points(phase: str, t: float, cfg: TorsatronConfig, n_scale: float = 1.0) -> list[dict]:
    """Toroidal plasma visualization points for VM canvas."""
    pts = []
    major_r = 90 + 10 * math.sin(t * 0.5)
    minor_r = 25 * n_scale
    count = 200 if phase == "burn" else 120

    for i in range(count):
        u = (i / count) * math.pi * 2
        v = ((i * 7) % count / count) * math.pi * 2 + t * (3 if phase == "burn" else 0.5)
        x = (major_r + minor_r * math.cos(v)) * math.cos(u)
        y = (major_r + minor_r * math.cos(v)) * math.sin(u)
        z = minor_r * math.sin(v) * 0.4

        if phase == "compression":
            sig = 0.3 + 0.4 * (t % 1.0)
            ptype = "rf"
        elif phase == "burn":
            sig = 0.85 + 0.15 * math.sin(v + t * 4)
            ptype = "lidar"
        elif phase == "expansion":
            sig = 0.5 * (1 - (t % 1.0))
            ptype = "gnss"
        else:
            sig = 0.2
            ptype = "rf"

        pts.append({"x": x, "y": y, "z": z, "sig": max(0.05, min(1.0, sig)), "type": ptype})
    return pts


def phase_plasma_state(phase: str, cfg: TorsatronConfig) -> tuple[float, float]:
    """Phase-specific density and B-field along adiabatic compression trajectory."""
    n_base = cfg.n_i_m3
    B_base = cfg.B_tesla
    if phase == "compression":
        n = OPTIMAL_BURN_N
    elif phase == "burn":
        n = OPTIMAL_BURN_N
    elif phase == "expansion":
        n = 2e21
    else:
        n = 1e21
    ratio = n / n_base if n_base else 1.0
    B = B_base * ratio ** (5 / 6)
    return n, B


def fusion_state_frame(phase: str, cfg: TorsatronConfig, Q: float) -> dict:
    """Physics metrics for VM fusion HUD."""
    n, B = phase_plasma_state(phase, cfg)
    phase_cfg = TorsatronConfig(
        volume_m3=cfg.volume_m3,
        n_i_m3=n,
        B_tesla=B,
        T_i_keV=cfg.T_i_keV,
        T_e_keV=cfg.T_e_keV,
        tau_burn_us=cfg.tau_burn_us,
        rep_rate_hz=cfg.rep_rate_hz,
        Z_eff=cfg.Z_eff,
    )

    bal = pulse_energy_balance(phase_cfg, Q_override=Q)
    tau_eq = spitzer_equipartition_s(n, cfg.T_e_keV, cfg.Z_eff, cfg.ln_lambda)
    ind = inductive_recovery(phase_cfg)
    sigma_bh = bosch_hale_d3he(cfg.T_i_keV)
    sigma_audit = 4.5e-22

    return {
        "phase": phase,
        "Q": Q,
        "B_T": round(B, 1),
        "n_e_m3": n,
        "T_i_keV": cfg.T_i_keV,
        "T_e_keV": cfg.T_e_keV,
        "tau_burn_us": cfg.tau_burn_us,
        "tau_eq_ms": round(tau_eq * 1e3, 4),
        "decoupling_margin": round(tau_eq / (cfg.tau_burn_us * 1e-6), 1),
        "net_MW": round(bal["continuous_MW"]["net_electrical"], 2),
        "gross_MW": round(bal["continuous_MW"]["gross_fusion"], 2),
        "recirc_pct": round(bal["recirculating_fraction"] * 100, 1),
        "hoop_MPa": round(bal["hoop_stress_MPa"], 0),
        "inductive_kJ": round(ind["inductive_recovery_kJ"], 1),
        "flux_diffusion_us": round(ind["flux_diffusion_time_us"], 1),
        "flux_conserved": ind["flux_conserved"],
        "rep_rate_hz": cfg.rep_rate_hz,
        "volume_m3": cfg.volume_m3,
        "sigma_v_bh": sigma_bh,
        "sigma_v_note": f"BH σv={sigma_bh:.1e} (audit 4.5e-22 is {sigma_audit/sigma_bh:.1f}× high)",
    }


def stream(target: str, port: int, hz: float, Q: float, volume: float):
    cfg = TorsatronConfig(volume_m3=volume)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    interval = 1.0 / max(hz, 0.1)
    t = 0.0
    phase_idx = 0

    print(f"[*] D-³He torsatron telemetry → {target}:{port} @ {hz}Hz Q={Q} V={volume}m³")

    try:
        while True:
            phase = PHASES[phase_idx % len(PHASES)]
            n_scale = 0.6 + 0.4 * (phase_idx % len(PHASES)) / len(PHASES)

            payload = {
                "mode": "torsatron",
                "anchor": ANCHOR,
                "t": round(t, 3),
                "fusion": fusion_state_frame(phase, cfg, Q),
                "points": torsatron_visual_points(phase, t, cfg, n_scale),
            }
            sock.sendto(json.dumps(payload).encode("utf-8"), (target, port))

            t += interval
            if int(t * 10) % 3 == 0:
                phase_idx += 1
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n[*] Fusion telemetry halted.")


def export_audit_json(path: str):
    report = run_full_audit()
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)
    print(f"[+] Audit exported: {path}")


def main():
    parser = argparse.ArgumentParser(description="D-³He fusion VM telemetry")
    parser.add_argument("--target", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=2368)
    parser.add_argument("--hz", type=float, default=10.0)
    parser.add_argument("--Q", type=float, default=15.0)
    parser.add_argument("--volume", type=float, default=0.1)
    parser.add_argument("--export", metavar="FILE", help="Export full audit JSON")
    args = parser.parse_args()

    if args.export:
        export_audit_json(args.export)
        return

    stream(args.target, args.port, args.hz, args.Q, args.volume)


if __name__ == "__main__":
    main()
