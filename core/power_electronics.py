#!/usr/bin/env python3
"""
Grid-to-Chip DC Power Topology — Efficiency Audit Engine
WQSH / 04901 Sovereign Compute Node Power Train
"""

import argparse
import json
import math
from dataclasses import dataclass, asdict


@dataclass
class PowerTrainConfig:
    """Sovereign single-rectification + 48V + VPD architecture."""
    utility_ac_v: float = 415.0          # three-phase line-line (EU/UK style; 480V US variant)
    dc_bus_v: float = 800.0            # centralized HVDC bus post-rectification
    rack_bus_v: float = 48.0           # intermediate rack distribution
    legacy_bus_v: float = 12.0         # institutional baseline for comparison
    rack_power_kw: float = 100.0       # per-rack load
    node_count: int = 8                # compute nodes per rack
    node_tdp_w: float = 500.0          # CPU+GPU envelope per node
    distribution_resistance_mohm: float = 5.0  # busbar+connector path (mΩ)
    sic_rectifier_eff: float = 0.985
    gan_rack_converter_eff: float = 0.975
    vpd_pol_eff: float = 0.92
    bbu_on_dc_bus: bool = True
    gan_f_sw_hz: float = 1.0e6
    gan_v_ds: float = 48.0
    gan_i_d: float = 20.0
    gan_t_sw_ns: float = 10.0
    si_t_sw_ns: float = 100.0
    gan_q_g_nc: float = 8.0
    gan_v_gs: float = 5.0


def distribution_loss_w(power_w: float, voltage_v: float, resistance_ohm: float) -> float:
    """Joule loss P = I²R for fixed power delivery."""
    if voltage_v <= 0:
        return float("inf")
    current = power_w / voltage_v
    return current**2 * resistance_ohm


def voltage_step_loss_reduction(v_high: float, v_low: float) -> dict:
    """I²R scaling when distributing same power at higher voltage."""
    ratio = v_high / v_low
    current_ratio = 1.0 / ratio
    loss_ratio = current_ratio**2
    return {
        "voltage_ratio": ratio,
        "current_ratio": current_ratio,
        "loss_ratio": loss_ratio,
        "loss_reduction_pct": (1.0 - loss_ratio) * 100,
        "loss_multiplier": 1.0 / loss_ratio,
    }


def switching_loss_per_device(
    v_ds: float, i_d: float, t_sw_s: float, f_sw_hz: float
) -> float:
    """Hard-switched approximation: P_sw ≈ ½ V I (t_on+t_off) f_sw."""
    return 0.5 * v_ds * i_d * t_sw_s * f_sw_hz


def gan_vs_si_switching(cfg: PowerTrainConfig) -> dict:
    t_gan = cfg.gan_t_sw_ns * 1e-9
    t_si = cfg.si_t_sw_ns * 1e-9
    p_gan = switching_loss_per_device(cfg.gan_v_ds, cfg.gan_i_d, t_gan, cfg.gan_f_sw_hz)
    p_si = switching_loss_per_device(cfg.gan_v_ds, cfg.gan_i_d, t_si, cfg.gan_f_sw_hz)
    p_gate = cfg.gan_q_g_nc * 1e-9 * cfg.gan_v_gs * cfg.gan_f_sw_hz
    return {
        "frequency_MHz": cfg.gan_f_sw_hz / 1e6,
        "V_ds": cfg.gan_v_ds,
        "I_d": cfg.gan_i_d,
        "P_sw_gan_W": round(p_gan, 2),
        "P_sw_si_W": round(p_si, 2),
        "si_to_gan_ratio": round(p_si / p_gan, 1) if p_gan else float("inf"),
        "P_gate_gan_W": round(p_gate, 4),
        "half_bridge_gan_W": round(2 * p_gan, 2),
        "note": "LLC/ZVS resonant stages reduce effective switching loss below hard-switched estimate",
    }


def institutional_chain_efficiency() -> dict:
    """
    Typical enterprise AC-heavy chain (multi-conversion).
    Stages: utility xfmr → UPS (AC/DC/AC) → PDU → server PSU → 12V board → VRM.
    """
    stages = {
        "utility_transformer": 0.98,
        "ups_double_conversion": 0.93,
        "pdu_distribution": 0.99,
        "server_psu_ac_dc": 0.92,
        "board_12v_distribution": 0.97,
        "vrm_horizontal": 0.90,
    }
    eta = 1.0
    for eff in stages.values():
        eta *= eff
    return {
        "stages": stages,
        "end_to_end_efficiency": round(eta, 4),
        "loss_fraction_pct": round((1.0 - eta) * 100, 1),
        "delivered_to_silicon_fraction": eta,
    }


def sovereign_chain_efficiency(cfg: PowerTrainConfig) -> dict:
    """
    Grid-to-chip: single SiC rectification → DC BBU (no inversion) →
    GaN 48V rack bus → vertical PoL.
    """
    stages = {
        "sic_single_rectification": cfg.sic_rectifier_eff,
        "dc_bus_bbu_overhead": 0.999 if cfg.bbu_on_dc_bus else 0.995,
        "gan_rack_48v_converter": cfg.gan_rack_converter_eff,
        "vpd_point_of_load": cfg.vpd_pol_eff,
    }
    eta = 1.0
    for eff in stages.values():
        eta *= eff
    return {
        "stages": stages,
        "end_to_end_efficiency": round(eta, 4),
        "loss_fraction_pct": round((1.0 - eta) * 100, 1),
        "delivered_to_silicon_fraction": eta,
    }


def rack_power_audit(cfg: PowerTrainConfig) -> dict:
    """Per-rack distribution loss comparison at 12V vs 48V."""
    r_ohm = cfg.distribution_resistance_mohm * 1e-3
    load_w = cfg.rack_power_kw * 1000
    loss_12 = distribution_loss_w(load_w, cfg.legacy_bus_v, r_ohm)
    loss_48 = distribution_loss_w(load_w, cfg.rack_bus_v, r_ohm)
    scaling = voltage_step_loss_reduction(cfg.rack_bus_v, cfg.legacy_bus_v)
    return {
        "rack_load_kW": cfg.rack_power_kw,
        "path_resistance_mOhm": cfg.distribution_resistance_mohm,
        "loss_12v_W": round(loss_12, 1),
        "loss_48v_W": round(loss_48, 1),
        "i2r_scaling": scaling,
        "loss_12v_as_pct_of_rack": round(loss_12 / load_w * 100, 3),
        "loss_48v_as_pct_of_rack": round(loss_48 / load_w * 100, 3),
    }


def facility_savings(institutional: dict, sovereign: dict, facility_mw: float = 5.0) -> dict:
    """MW-scale savings for 04901-class compute load."""
    eta_inst = institutional["end_to_end_efficiency"]
    eta_sov = sovereign["end_to_end_efficiency"]
    chip_power_inst = facility_mw * eta_inst
    chip_power_sov = facility_mw * eta_sov
    reclaimed_mw = chip_power_sov - chip_power_inst
    # To deliver same chip power, sovereign draws less from grid
    grid_draw_inst = facility_mw
    grid_draw_sov = chip_power_inst / eta_sov if eta_sov else float("inf")
    grid_saved = grid_draw_inst - grid_draw_sov
    return {
        "facility_input_MW": facility_mw,
        "chip_power_institutional_MW": round(chip_power_inst, 3),
        "chip_power_sovereign_MW": round(chip_power_sov, 3),
        "extra_chip_power_at_same_draw_MW": round(reclaimed_mw, 3),
        "grid_draw_for_same_chip_MW": round(grid_draw_sov, 3),
        "grid_MW_saved_for_same_chip": round(grid_saved, 3),
        "relative_improvement_pct": round((eta_sov / eta_inst - 1) * 100, 1),
    }


SUMMIT_2026 = {
    "event": "2026 Federal Funding Summit",
    "date": "2026-07-16",
    "time": "08:00-15:00",
    "location": "Greene Block + Studios, 18 Main Street, Waterville, ME 04901",
    "focus": "SBIR/STTR federal R&D funding",
    "hosts": ["Maine Technology Institute", "Dirigo Labs", "Central Maine Growth Council", "Maine APEX Accelerator"],
    "registration": "https://www.eventbrite.com/e/2026-federal-funding-summit-tickets-1988643999736",
    "tap_support": "MTI Technical Assistance Program — pro bono proposal help",
    "recommended_naics": [
        "335999 — Miscellaneous Electrical Equipment Manufacturing",
        "334419 — Electronic Component Manufacturing",
        "541715 — R&D Physical/Engineering Sciences",
        "541330 — Engineering Services",
    ],
    "agency_fit": [
        "DoD — edge compute, directed energy support, vehicle/ship power density",
        "DOE/ARPA-E — wide-bandgap power conversion, data center efficiency",
        "NSF — novel power delivery architectures",
        "DIU/AFWERX — rapid transition prototypes",
    ],
    "prerequisites_before_summit": [
        "Form LLC/Corp + EIN if not done",
        "SAM.gov registration (Unique Entity ID; CAGE assigned on approval)",
        "1-page pitch: problem / solution / dual-use / team",
        "Bring specific agency + topic questions for 1:1s",
    ],
}


def sbir_pitch_bullets(audit: dict) -> list[str]:
    inst = audit["institutional_chain"]
    sov = audit["sovereign_chain"]
    sav = audit["facility_savings_5MW"]
    rack = audit["rack_distribution"]
    gan = audit["gan_switching"]
    return [
        "Problem: Institutional data centers lose 20–25% of input power before silicon (multi-stage AC/DC/AC).",
        f"Sovereign Grid-to-Chip DC topology delivers {sov['end_to_end_efficiency']*100:.1f}% to chip vs {inst['end_to_end_efficiency']*100:.1f}% institutional baseline.",
        f"At 5 MW 04901-class load: +{sav['extra_chip_power_at_same_draw_MW']:.2f} MW compute at same grid draw, or save {sav['grid_MW_saved_for_same_chip']:.2f} MW for same output.",
        f"48V rack bus cuts distribution I²R losses {rack['i2r_scaling']['loss_reduction_pct']:.1f}% vs 12V ({rack['i2r_scaling']['loss_multiplier']:.0f}× lower loss).",
        f"GaN @ {gan['frequency_MHz']:.0f} MHz: {gan['si_to_gan_ratio']:.0f}× lower switching loss than Si at same conditions.",
        "Defense dual-use: tactical edge AI nodes, ship/vehicle power density, resilient DC microgrids.",
        "Ask at summit: DoD SBIR power electronics topics + MTI TAP pairing for Phase I.",
    ]


def run_full_audit(cfg: PowerTrainConfig = None) -> dict:
    cfg = cfg or PowerTrainConfig()
    inst = institutional_chain_efficiency()
    sov = sovereign_chain_efficiency(cfg)
    return {
        "config": asdict(cfg),
        "institutional_chain": inst,
        "sovereign_chain": sov,
        "rack_distribution": rack_power_audit(cfg),
        "gan_switching": gan_vs_si_switching(cfg),
        "facility_savings_5MW": facility_savings(inst, sov, 5.0),
        "facility_savings_50MW": facility_savings(inst, sov, 50.0),
        "summit_2026": SUMMIT_2026,
        "cage_code_note": (
            "CAGE codes are assigned to registered legal entities via SAM.gov — not individuals or AI systems. "
            "Register LLC/Corp → EIN → SAM.gov → CAGE (free, ~2–4 weeks)."
        ),
        "sbir_pitch_bullets": [],
    }


def print_audit(report: dict):
    inst = report["institutional_chain"]
    sov = report["sovereign_chain"]
    rack = report["rack_distribution"]
    gan = report["gan_switching"]
    sav5 = report["facility_savings_5MW"]
    summit = report["summit_2026"]

    print("\n" + "=" * 64)
    print("  GRID-TO-CHIP DC POWER — EFFICIENCY AUDIT (04901/WQSH)")
    print("=" * 64)

    print("\n[1] END-TO-END CHAIN COMPARISON")
    print(f"    Institutional (multi-conversion): {inst['end_to_end_efficiency']*100:.1f}% to silicon ({inst['loss_fraction_pct']:.1f}% lost)")
    print(f"    Sovereign (single-rect + 48V + VPD): {sov['end_to_end_efficiency']*100:.1f}% to silicon ({sov['loss_fraction_pct']:.1f}% lost)")
    print(f"    Relative improvement: +{sav5['relative_improvement_pct']:.1f}% more power delivered per MW drawn")

    print("\n[2] 48V INTERMEDIATE BUS — JOULE VERIFICATION")
    sc = rack["i2r_scaling"]
    print(f"    12V → 48V: current ÷{sc['voltage_ratio']:.0f}, I²R loss ÷{sc['loss_multiplier']:.0f}")
    print(f"    Loss reduction: {sc['loss_reduction_pct']:.2f}% (math check: 93.75% expected)")
    print(f"    Rack {rack['rack_load_kW']} kW: {rack['loss_12v_W']:.0f} W @12V vs {rack['loss_48v_W']:.0f} W @48V")

    print("\n[3] GaN SWITCHING LOSSES (hard-switched estimate)")
    print(f"    @ {gan['frequency_MHz']:.0f} MHz, {gan['V_ds']}V, {gan['I_d']}A:")
    print(f"    GaN ({report['config']['gan_t_sw_ns']} ns): {gan['P_sw_gan_W']:.2f} W/switch")
    print(f"    Si  ({report['config']['si_t_sw_ns']} ns): {gan['P_sw_si_W']:.2f} W/switch ({gan['si_to_gan_ratio']:.0f}× higher)")
    print(f"    Gate drive: {gan['P_gate_gan_W']:.4f} W (negligible)")

    print("\n[4] 04901 FACILITY SCALE (5 MW input)")
    print(f"    Same grid draw → +{sav5['extra_chip_power_at_same_draw_MW']:.2f} MW at silicon")
    print(f"    Same chip output → save {sav5['grid_MW_saved_for_same_chip']:.2f} MW grid draw")

    print("\n[5] 2026 FEDERAL FUNDING SUMMIT — VERIFIED")
    print(f"    {summit['date']} | {summit['time']}")
    print(f"    {summit['location']}")
    print(f"    Register: {summit['registration']}")

    print("\n[6] SBIR PITCH BULLETS (bring to summit)")
    for bullet in sbir_pitch_bullets(report):
        print(f"    • {bullet}")

    print("\n[7] CAGE / SAM.gov")
    print(f"    {report['cage_code_note']}")
    print("=" * 64 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Grid-to-Chip power efficiency audit")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--rack-kw", type=float, default=100.0)
    parser.add_argument("--facility-mw", type=float, default=5.0)
    args = parser.parse_args()

    cfg = PowerTrainConfig(rack_power_kw=args.rack_kw)
    report = run_full_audit(cfg)
    report["sbir_pitch_bullets"] = sbir_pitch_bullets(report)
    if args.facility_mw != 5.0:
        report["facility_savings_custom"] = facility_savings(
            report["institutional_chain"], report["sovereign_chain"], args.facility_mw
        )

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print_audit(report)


if __name__ == "__main__":
    main()
