#!/usr/bin/env python3
"""
Dickey.OS Sovereign Core - Master Integration Module
Strictly Local Execution Protocol
"""

import argparse
import os
import sys
import time
from datetime import datetime

try:
    import ollama
except ImportError:
    print("[!] Critical Failure: Local AI dependency missing. Run: pip install ollama")
    sys.exit(1)

from galactic_nav import GalacticNavSystem, run_demo as nav_demo
from digital_twin_ingest import DigitalTwinIngest
from threat_intel_cvss import ThreatIntelCVSS
from logistics_matrix import LogisticsMatrix
from fusion_physics import run_full_audit, print_audit
from power_electronics import run_full_audit as run_power_audit, print_audit as print_power_audit
from tactile_qctb import run_full_audit as run_tactile_audit, print_audit as print_tactile_audit
from vm_bridge import emit_telemetry, emit_fusion_telemetry, emit_tactile_telemetry, grid_status


class SovereignCoreIntegrator:
    def __init__(self, ai_model="llama3"):
        self.ai_model = ai_model
        self.boot_time = time.time()
        self.log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
        os.makedirs(self.log_dir, exist_ok=True)
        self.nav = GalacticNavSystem(ai_model=ai_model)
        self.twin = DigitalTwinIngest()
        self.threat = ThreatIntelCVSS(ai_model=ai_model)
        self.logistics = LogisticsMatrix()
        self.active_subsystems = {
            "Digital Twin (Godot/PostGIS)": "Standby",
            "Galactic Navigation (SNN)": "Active",
            "Threat Intel (CVSS)": "Standby",
            "Logistics (Emergency Contractors/04901 Taxi)": "Standby",
            "Fusion Physics (D-³He Torsatron)": "Active",
            "Grid-to-Chip Power (GaN/SiC)": "Active",
            "QCTB Tactile Edge (TensorRT)": "Active",
            "Sovereign CTI (UNC5792/UNC4221)": "Standby",
            "04901 VM Game Engine": "Standby",
        }
        print("[*] Dickey.OS Sovereign Core Initialized.")

    def _log_event(self, message):
        stamp = datetime.now().strftime("%m%d%Y")
        log_path = os.path.join(self.log_dir, f"{stamp}_system_init.log")
        with open(log_path, "a", encoding="utf-8") as fh:
            fh.write(f"[{datetime.now().isoformat()}] {message}\n")

    def query_central_intelligence(self, context, query):
        try:
            response = ollama.chat(model=self.ai_model, messages=[
                {"role": "system", "content": "You are the central AI architecture for Dickey.OS."},
                {"role": "user", "content": f"Context: {context}\nCommand: {query}"},
            ])
            return response["message"]["content"]
        except Exception as e:
            return f"[!] Local routing failure: {str(e)}"

    def print_system_status(self):
        print("\n=== DICKEY.OS CORE STATUS ===")
        for system, status in self.active_subsystems.items():
            print(f"[{status}] {system}")
        print(f"Uptime: {round(time.time() - self.boot_time, 2)}s\n")


def main():
    parser = argparse.ArgumentParser(description="Dickey.OS Master Integration")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--analyze", type=str, metavar="QUERY")
    parser.add_argument("--nav-demo", action="store_true")
    parser.add_argument("--fusion-audit", action="store_true")
    parser.add_argument("--power-audit", action="store_true")
    parser.add_argument("--tactile-audit", action="store_true")
    parser.add_argument("--model", type=str, default="llama3")
    args = parser.parse_args()
    core = SovereignCoreIntegrator(ai_model=args.model)
    if args.status:
        core.print_system_status()
    if args.nav_demo:
        nav_demo(ai_model=args.model)
    if args.fusion_audit:
        print_audit(run_full_audit())
    if args.power_audit:
        print_power_audit(run_power_audit())
    if args.tactile_audit:
        print_tactile_audit(run_tactile_audit())
    if args.analyze:
        print(core.query_central_intelligence("Cross-System", args.analyze))
    if len(sys.argv) <= 1:
        parser.print_help()


if __name__ == "__main__":
    main()
