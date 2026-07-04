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
        print(f"[*] Local Intelligence Routing via: {self.ai_model}")

    def _log_event(self, message):
        stamp = datetime.now().strftime("%m%d%Y")
        log_path = os.path.join(self.log_dir, f"{stamp}_system_init.log")
        with open(log_path, "a", encoding="utf-8") as fh:
            fh.write(f"[{datetime.now().isoformat()}] {message}\n")

    def query_central_intelligence(self, context, query):
        """Routes global system queries to the local LLM."""
        print(f"\n[*] Consulting Core Intelligence on [{context}]...")
        try:
            response = ollama.chat(
                model=self.ai_model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are the central AI architecture for Dickey.OS. You manage Waterville district "
                            "digital twins, cyber threat intelligence, physical construction logistics, and spatial "
                            "navigation. Prioritize local-first, air-gapped security and operational efficiency."
                        ),
                    },
                    {"role": "user", "content": f"Context: {context}\nCommand: {query}"},
                ],
            )
            result = response["message"]["content"]
            self._log_event(f"ANALYZE [{context}]: {query[:120]}")
            return result
        except Exception as e:
            return f"[!] Local routing failure: {str(e)}"

    def run_nav_subsystem(self):
        self.active_subsystems["Galactic Navigation (SNN)"] = "Active"
        self._log_event("NAV subsystem demo initiated")
        return nav_demo(ai_model=self.ai_model)

    def run_twin_ingest(self, source_path):
        self.active_subsystems["Digital Twin (Godot/PostGIS)"] = "Active"
        self._log_event(f"TWIN ingest: {source_path}")
        if source_path.endswith((".pcap", ".pcapng")):
            return self.twin.ingest_pcap_tof(source_path)
        return self.twin.ingest_las(source_path)

    def run_threat_score(self, cve_path):
        self.active_subsystems["Threat Intel (CVSS)"] = "Active"
        self._log_event(f"THREAT score: {cve_path}")
        return self.threat.ingest_file(cve_path)

    def run_logistics_status(self):
        self.active_subsystems["Logistics (Emergency Contractors/04901 Taxi)"] = "Active"
        self._log_event("LOGISTICS status matrix printed")
        self.logistics.print_status_matrix()
        return self.logistics

    def print_system_status(self):
        print("\n==============================================")
        print("   DICKEY.OS CORE - SUBSYSTEM STATUS MATRIX   ")
        print("==============================================")
        for system, status in self.active_subsystems.items():
            indicator = "[+]" if status == "Active" else "[-]"
            print(f"{indicator} {system}: {status}")
        uptime = round(time.time() - self.boot_time, 2)
        print(f"[*] Core uptime: {uptime}s")
        print("==============================================\n")
        self._log_event("STATUS matrix printed")


def main():
    parser = argparse.ArgumentParser(description="Dickey.OS Master Integration Command Line")
    parser.add_argument("--status", action="store_true", help="Print subsystem status matrix")
    parser.add_argument("--analyze", type=str, metavar="QUERY", help="Route a cross-system query to the local LLM")
    parser.add_argument("--nav-demo", action="store_true", help="Run Galactic Nav SNN telemetry + trajectory demo")
    parser.add_argument("--twin-ingest", type=str, metavar="FILE", help="Ingest LiDAR (.las) or ToF PCAP into digital twin")
    parser.add_argument("--threat-score", type=str, metavar="FILE", help="Score local CVE JSON offline")
    parser.add_argument("--logistics-status", action="store_true", help="Print contractor/taxi logistics matrix")
    parser.add_argument("--fusion-audit", action="store_true", help="Run D-³He pulsed torsatron physics audit")
    parser.add_argument("--power-audit", action="store_true", help="Run Grid-to-Chip DC power efficiency audit")
    parser.add_argument("--power-export", type=str, metavar="FILE", help="Export power audit JSON for SBIR/summit")
    parser.add_argument("--tactile-audit", action="store_true", help="Run QCTB tactile/TensorRT architecture audit")
    parser.add_argument("--tactile-export", type=str, metavar="FILE", help="Export QCTB audit JSON")
    parser.add_argument("--tactile-ansatz", type=str, metavar="FILE", help="Export PennyLane VQC ansatz")
    parser.add_argument("--tactile-stream", action="store_true", help="Stream QCTB tactile state to 04901 VM")
    parser.add_argument("--fusion-stream", action="store_true", help="Stream D-³He physics to 04901 VM over UDP")
    parser.add_argument("--fusion-Q", type=float, default=15.0, help="Fusion Q for telemetry stream")
    parser.add_argument("--fusion-export", type=str, metavar="FILE", help="Export audit JSON for VM/archive")
    parser.add_argument("--cti-status", action="store_true", help="Sovereign CTI database stats")
    parser.add_argument("--cti-math", action="store_true", help="CTI pipeline resource mathematics")
    parser.add_argument("--cti-rag", action="store_true", help="Generate CTI graph Markdown for Ollama RAG")
    parser.add_argument("--cti-crypto", action="store_true", help="Crypto wallet graph report")
    parser.add_argument("--cti-correlate", type=str, metavar="QUERY", help="Ollama CTI correlation query")
    parser.add_argument("--vm-status", action="store_true", help="04901 Sovereign VM grid status")
    parser.add_argument("--vm-emit", action="store_true", help="Start UDP telemetry emitter to VM proxy")
    parser.add_argument("--vm-mode", type=str, default="fusion", choices=["lidar", "gnss", "rf", "fusion"])
    parser.add_argument("--vm-target", type=str, default="127.0.0.1", help="UDP target (Tailscale IP)")
    parser.add_argument("--model", type=str, default="llama3", help="Local Ollama model (default: llama3)")

    args = parser.parse_args()
    core = SovereignCoreIntegrator(ai_model=args.model)

    if args.status:
        core.print_system_status()

    if args.nav_demo:
        core.run_nav_subsystem()

    if args.twin_ingest:
        core.run_twin_ingest(args.twin_ingest)

    if args.threat_score:
        core.run_threat_score(args.threat_score)

    if args.logistics_status:
        core.run_logistics_status()

    if args.fusion_audit:
        core._log_event("FUSION physics audit executed")
        print_audit(run_full_audit())

    if args.power_audit:
        core.active_subsystems["Grid-to-Chip Power (GaN/SiC)"] = "Active"
        core._log_event("POWER electronics audit executed")
        print_power_audit(run_power_audit())

    if args.power_export:
        import json
        from power_electronics import sbir_pitch_bullets
        report = run_power_audit()
        report["sbir_pitch_bullets"] = sbir_pitch_bullets(report)
        with open(args.power_export, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2)
        print(f"[+] Power audit exported: {args.power_export}")

    if args.tactile_audit:
        core.active_subsystems["QCTB Tactile Edge (TensorRT)"] = "Active"
        core._log_event("QCTB tactile architecture audit executed")
        print_tactile_audit(run_tactile_audit())

    if args.tactile_export:
        import json
        report = run_tactile_audit()
        with open(args.tactile_export, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2)
        print(f"[+] QCTB audit exported: {args.tactile_export}")

    if args.tactile_ansatz:
        report = run_tactile_audit()
        with open(args.tactile_ansatz, "w", encoding="utf-8") as fh:
            fh.write(report["pennylane_ansatz"])
        print(f"[+] PennyLane VQC ansatz: {args.tactile_ansatz}")

    if args.fusion_export:
        import json
        report = run_full_audit()
        with open(args.fusion_export, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2)
        print(f"[+] Fusion audit exported: {args.fusion_export}")

    if args.tactile_stream:
        core.active_subsystems["QCTB Tactile Edge (TensorRT)"] = "Active"
        core.active_subsystems["04901 VM Game Engine"] = "Active"
        core._log_event(f"TACTILE stream target={args.vm_target}")
        proc = emit_tactile_telemetry(target=args.vm_target)
        if proc:
            print("[*] Tactile telemetry streaming — Ctrl+C to stop")
            try:
                proc.wait()
            except KeyboardInterrupt:
                proc.terminate()

    if args.fusion_stream:
        core.active_subsystems["Fusion Physics (D-³He Torsatron)"] = "Active"
        core.active_subsystems["04901 VM Game Engine"] = "Active"
        core._log_event(f"FUSION stream Q={args.fusion_Q} target={args.vm_target}")
        proc = emit_fusion_telemetry(target=args.vm_target, Q=args.fusion_Q)
        if proc:
            print("[*] Fusion telemetry streaming — Ctrl+C to stop")
            try:
                proc.wait()
            except KeyboardInterrupt:
                proc.terminate()

    if args.cti_status or args.cti_math or args.cti_rag or args.cti_crypto or args.cti_correlate:
        from cti_bridge import (
            run_cti_status,
            run_cti_rag,
            run_cti_math,
            run_cti_correlate,
            run_cti_crypto_report,
        )

    if args.cti_status:
        core.active_subsystems["Sovereign CTI (UNC5792/UNC4221)"] = "Active"
        core._log_event("CTI status queried")
        run_cti_status()

    if args.cti_math:
        core.active_subsystems["Sovereign CTI (UNC5792/UNC4221)"] = "Active"
        run_cti_math()

    if args.cti_rag:
        core.active_subsystems["Sovereign CTI (UNC5792/UNC4221)"] = "Active"
        core._log_event("CTI RAG export generated")
        run_cti_rag()

    if args.cti_crypto:
        core.active_subsystems["Sovereign CTI (UNC5792/UNC4221)"] = "Active"
        run_cti_crypto_report()

    if args.cti_correlate:
        core.active_subsystems["Sovereign CTI (UNC5792/UNC4221)"] = "Active"
        core._log_event(f"CTI correlate: {args.cti_correlate[:80]}")
        run_cti_correlate(args.cti_correlate, model=args.model)

    if args.vm_status:
        core.active_subsystems["04901 VM Game Engine"] = "Active"
        print("\n--- 04901 VM GRID STATUS ---")
        grid_status()
        print("----------------------------\n")

    if args.vm_emit:
        core.active_subsystems["04901 VM Game Engine"] = "Active"
        core._log_event(f"VM emit mode={args.vm_mode} target={args.vm_target}")
        proc = emit_telemetry(mode=args.vm_mode, target=args.vm_target)
        if proc:
            print("[*] Emitter running — Ctrl+C to stop")
            try:
                proc.wait()
            except KeyboardInterrupt:
                proc.terminate()

    if args.analyze:
        directive = core.query_central_intelligence("Cross-System Integration", args.analyze)
        print("\n--- CORE DIRECTIVE ---")
        print(directive)
        print("----------------------\n")

    if len(sys.argv) <= 1:
        parser.print_help()


if __name__ == "__main__":
    main()