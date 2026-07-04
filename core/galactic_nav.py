#!/usr/bin/env python3
"""
Galactic Flight and Time Navigation System - Core Engine
Strictly Local Execution Protocol
"""

import json
import math
import struct
import time
import sys

try:
    import ollama
except ImportError:
    print("[!] Critical Failure: Local AI dependency missing.")
    print("    Resolve via: pip install ollama")
    sys.exit(1)


class SNNTelemetryParser:
    """Event-driven telemetry parser for neuromorphic navigation feeds."""

    SPIKE_HEADER = b"SNN1"

    def __init__(self):
        self.spike_buffer = []
        self.last_spike_epoch = None

    def parse_binary_frame(self, payload):
        """
        Parse raw SNN telemetry frames.
        Format: 4-byte magic (SNN1) + uint32 spike_count + float32 coords (x,y,z,t_flux)
        """
        if len(payload) < 24 or not payload.startswith(self.SPIKE_HEADER):
            return None

        spike_count = struct.unpack_from("<I", payload, 4)[0]
        coords = struct.unpack_from("<4f", payload, 8)
        spike = {
            "x": coords[0],
            "y": coords[1],
            "z": coords[2],
            "t_flux": coords[3],
            "spike_count": spike_count,
            "epoch": time.time(),
        }
        self.spike_buffer.append(spike)
        self.last_spike_epoch = spike["epoch"]
        return spike

    def parse_json_telemetry(self, raw_json):
        """Accept JSON telemetry from RF-to-SNN translation pipelines."""
        if isinstance(raw_json, (bytes, bytearray)):
            raw_json = raw_json.decode("utf-8")
        data = json.loads(raw_json)

        spike = {
            "x": float(data.get("x", 0.0)),
            "y": float(data.get("y", 0.0)),
            "z": float(data.get("z", 0.0)),
            "t_flux": float(data.get("t_flux", time.time())),
            "spike_count": int(data.get("spike_count", 1)),
            "epoch": time.time(),
        }
        self.spike_buffer.append(spike)
        self.last_spike_epoch = spike["epoch"]
        return spike

    def get_filtered_anchor(self, decay_window=5.0):
        """Return the most recent spike within the temporal decay window."""
        if not self.spike_buffer:
            return None

        now = time.time()
        recent = [s for s in self.spike_buffer if (now - s["epoch"]) <= decay_window]
        if not recent:
            return self.spike_buffer[-1]
        return max(recent, key=lambda s: s["spike_count"])


class GalacticNavSystem:
    def __init__(self, ai_model="llama3"):
        self.ai_model = ai_model
        self.telemetry_parser = SNNTelemetryParser()
        self.current_telemetry = {
            "x": 0.0,
            "y": 0.0,
            "z": 0.0,
            "t_flux": time.time(),
        }
        print(f"[*] Navigation Core Initialized. AI Engine: {self.ai_model} (Air-gapped)")

    def ingest_telemetry(self, payload, format_hint="auto"):
        """Route raw SNN telemetry into the navigation anchor."""
        if format_hint == "json" or (
            format_hint == "auto" and isinstance(payload, (str, bytes)) and payload[:1] in (b"{", "{")
        ):
            spike = self.telemetry_parser.parse_json_telemetry(payload)
        else:
            if isinstance(payload, str):
                payload = payload.encode("latin-1")
            spike = self.telemetry_parser.parse_binary_frame(payload)

        if spike:
            self.current_telemetry = {
                "x": spike["x"],
                "y": spike["y"],
                "z": spike["z"],
                "t_flux": spike["t_flux"],
            }
            print(f"[+] SNN anchor locked: ({spike['x']}, {spike['y']}, {spike['z']}) spikes={spike['spike_count']}")
            return spike

        print("[!] Telemetry frame rejected — invalid SNN signature.")
        return None

    def calculate_jump_vector(self, target_coords):
        """Calculates Euclidean distance and temporal variance for the jump."""
        print(f"[*] Calculating trajectory to {target_coords}...")

        spatial_distance = math.sqrt(
            (target_coords["x"] - self.current_telemetry["x"]) ** 2
            + (target_coords["y"] - self.current_telemetry["y"]) ** 2
            + (target_coords["z"] - self.current_telemetry["z"]) ** 2
        )

        temporal_delta = target_coords.get("t_flux", time.time()) - self.current_telemetry["t_flux"]

        return {
            "distance": round(spatial_distance, 4),
            "t_delta": round(temporal_delta, 4),
            "origin": dict(self.current_telemetry),
            "target": target_coords,
        }

    def consult_onboard_ai(self, query):
        """Processes navigation queries through the local LLM."""
        print(f"\n[*] Bridging query to local {self.ai_model} instance...")

        try:
            response = ollama.chat(
                model=self.ai_model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are the onboard AI for a sovereign, air-gapped galactic navigation system. "
                            "Provide highly technical, concise trajectory and temporal shielding directives."
                        ),
                    },
                    {"role": "user", "content": query},
                ],
            )
            return response["message"]["content"]
        except Exception as e:
            return f"[!] AI Core communication failure: {str(e)}"


def run_demo(ai_model="llama3"):
    nav = GalacticNavSystem(ai_model=ai_model)

    snn_frame = SNNTelemetryParser.SPIKE_HEADER + struct.pack(
        "<I4f", 42, 12.5, -8.3, 100.0, time.time()
    )
    nav.ingest_telemetry(snn_frame, format_hint="binary")

    target_vector = {
        "x": 1045.8,
        "y": -332.1,
        "z": 890.5,
        "t_flux": time.time() + 86400,
    }

    telemetry = nav.calculate_jump_vector(target_vector)
    print(
        f"[+] Trajectory Locked. Spatial Jump: {telemetry['distance']} units. "
        f"Temporal Shift: {telemetry['t_delta']}s."
    )

    scenario_query = (
        f"We are initiating a jump spanning {telemetry['distance']} spatial units "
        f"with a {telemetry['t_delta']} second temporal shift. Recommend power distribution "
        f"for the deflector arrays and local network shielding."
    )

    ai_directive = nav.consult_onboard_ai(scenario_query)

    print("\n--- AI DIRECTIVE ---")
    print(ai_directive)
    print("--------------------\n")
    print("[*] Ready for push to master.")
    return telemetry


if __name__ == "__main__":
    run_demo()
