#!/usr/bin/env python3
"""
04901 Digital Twin Engine — PostGIS/LiDAR Godot Bridge
Strictly Local Execution Protocol
"""

import json
import os
import sys
from datetime import datetime


class DigitalTwinIngest:
    """Ingest LiDAR/ToF point clouds and emit PostGIS-ready + Godot payloads."""

    WATERVILLE_ORIGIN = {"lat": 44.5523, "lon": -69.6317, "epsg": 4326}

    def __init__(self, output_dir="data/twin_exports"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        self.point_count = 0
        self.bounds = None
        print("[*] Digital Twin Ingest initialized (PostGIS/Godot bridge)")

    def _update_bounds(self, points):
        if len(points) == 0:
            return
        xs, ys, zs = points[:, 0], points[:, 1], points[:, 2]
        self.bounds = {
            "xmin": float(xs.min()),
            "xmax": float(xs.max()),
            "ymin": float(ys.min()),
            "ymax": float(ys.max()),
            "zmin": float(zs.min()),
            "zmax": float(zs.max()),
        }

    def ingest_las(self, las_path):
        """Load a .las point cloud and prepare sovereign export artifacts."""
        try:
            import laspy
            import numpy as np
        except ImportError:
            print("[!] Missing dependency: pip install laspy numpy")
            return None

        if not os.path.isfile(las_path):
            print(f"[!] Source file missing: {las_path}")
            return None

        print(f"[*] Ingesting LiDAR archive: {las_path}")
        las = laspy.read(las_path)
        points = np.vstack((las.x, las.y, las.z)).transpose()
        self.point_count = len(points)
        self._update_bounds(points)

        base = os.path.splitext(os.path.basename(las_path))[0]
        godot_json = os.path.join(self.output_dir, f"{base}_godot_grid.json")
        postgis_sql = os.path.join(self.output_dir, f"{base}_postgis.sql")

        grid_payload = {
            "district": "04901",
            "origin": self.WATERVILLE_ORIGIN,
            "point_count": self.point_count,
            "bounds": self.bounds,
            "sample_points": points[: min(500, self.point_count)].tolist(),
            "exported_at": datetime.now().isoformat(),
        }

        with open(godot_json, "w", encoding="utf-8") as fh:
            json.dump(grid_payload, fh, indent=2)

        self._write_postgis_sql(postgis_sql, base)

        print(f"[+] Godot grid payload: {godot_json}")
        print(f"[+] PostGIS DDL stub:   {postgis_sql}")
        print(f"[+] Sovereign point cloud: {self.point_count} points ingested")

        return {
            "point_count": self.point_count,
            "bounds": self.bounds,
            "godot_json": godot_json,
            "postgis_sql": postgis_sql,
        }

    def ingest_pcap_tof(self, pcap_path, output_las=None):
        """Extract Android ToF depth packets from PCAP and chain to LAS ingest."""
        try:
            import numpy as np
            from scapy.all import UDP, rdpcap
        except ImportError:
            print("[!] Missing dependency: pip install scapy numpy")
            return None

        if not os.path.isfile(pcap_path):
            print(f"[!] PCAP source missing: {pcap_path}")
            return None

        print(f"[*] Parsing ToF binary stream: {pcap_path}")
        packets = rdpcap(pcap_path)
        points = []

        for pkt in packets:
            if pkt.haslayer(UDP) and len(pkt[UDP].payload) >= 16:
                payload = bytes(pkt[UDP].payload)
                try:
                    raw_data = np.frombuffer(payload[8:], dtype=np.float32)
                    reshaped = raw_data[: (len(raw_data) // 3) * 3].reshape(-1, 3)
                    if len(reshaped) > 0:
                        points.extend(reshaped)
                except Exception:
                    continue

        if not points:
            print("[!] Ingestion failed: no valid ToF signature in PCAP.")
            return None

        try:
            import laspy
        except ImportError:
            print("[!] Missing dependency: pip install laspy")
            return None

        points = np.array(points)
        if output_las is None:
            base = os.path.splitext(os.path.basename(pcap_path))[0]
            output_las = os.path.join(self.output_dir, f"{base}.las")

        header = laspy.LasHeader(point_format=3, version="1.2")
        las = laspy.LasData(header)
        las.x = points[:, 0]
        las.y = points[:, 1]
        las.z = points[:, 2]
        las.write(output_las)
        print(f"[+] Intermediate LAS written: {output_las}")

        return self.ingest_las(output_las)

    def _write_postgis_sql(self, sql_path, table_base):
        """Emit a local PostGIS table stub for sovereign deployment."""
        table = f"twin_{table_base}".replace("-", "_")
        sql = f"""-- Dickey.OS 04901 Digital Twin — PostGIS stub
-- Execute against local sovereign Postgres/PostGIS instance

CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS {table} (
    id SERIAL PRIMARY KEY,
    geom GEOMETRY(POINTZ, 4326),
    district TEXT DEFAULT '04901',
    ingested_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_{table}_geom ON {table} USING GIST (geom);

-- Bounds reference: {json.dumps(self.bounds)}
-- Point count: {self.point_count}
"""
        with open(sql_path, "w", encoding="utf-8") as fh:
            fh.write(sql)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 digital_twin_ingest.py <file.las|file.pcap>")
        sys.exit(1)

    ingest = DigitalTwinIngest()
    source = sys.argv[1]
    if source.endswith(".pcap") or source.endswith(".pcapng"):
        ingest.ingest_pcap_tof(source)
    else:
        ingest.ingest_las(source)