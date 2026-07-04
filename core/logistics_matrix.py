#!/usr/bin/env python3
"""
Maine Emergency Contractors & 04901 Taxi Logistics Matrix
Strictly Local Execution Protocol
"""

import json
import time
from datetime import datetime


class LogisticsMatrix:
    """Hardware procurement, contractor allocation, and local taxi dispatch routing."""

    CONTRACTOR_POOL = {
        "MEC-001": {"name": "Maine Emergency Contractors", "status": "Available", "crew": 4},
        "MEC-002": {"name": "Dickey Structural Build", "status": "On-Site", "crew": 2},
        "MEC-003": {"name": "Waterville Hardware Procurement", "status": "Standby", "crew": 1},
    }

    TAXI_ROUTES = {
        "TAXI-04901-A": {"origin": "Downtown Waterville", "dest": "Kennedy Memorial", "eta_min": 8},
        "TAXI-04901-B": {"origin": "Elm Plaza", "dest": "Inland Hospital", "eta_min": 12},
        "TAXI-04901-C": {"origin": "Colby College", "dest": "Oakland Ave District", "eta_min": 15},
    }

    def __init__(self):
        self.allocations = []
        self.procurement_queue = []
        self.boot_time = time.time()
        print("[*] Logistics Matrix initialized (04901 district)")

    def assign_contractor(self, job_id, contractor_id, resource_type, units=1):
        contractor = self.CONTRACTOR_POOL.get(contractor_id)
        if not contractor:
            print(f"[!] Unknown contractor: {contractor_id}")
            return None

        allocation = {
            "job_id": job_id,
            "contractor_id": contractor_id,
            "contractor_name": contractor["name"],
            "resource_type": resource_type,
            "units": units,
            "assigned_at": datetime.now().isoformat(),
            "status": "Allocated",
        }
        self.allocations.append(allocation)
        print(f"[+] {contractor['name']} assigned to {job_id} ({resource_type} x{units})")
        return allocation

    def queue_procurement(self, sku, quantity, priority="NORMAL"):
        item = {
            "sku": sku,
            "quantity": quantity,
            "priority": priority,
            "queued_at": datetime.now().isoformat(),
            "status": "Queued",
        }
        self.procurement_queue.append(item)
        print(f"[+] Procurement queued: {sku} x{quantity} [{priority}]")
        return item

    def dispatch_taxi(self, route_id, passenger_count=1):
        route = self.TAXI_ROUTES.get(route_id)
        if not route:
            print(f"[!] Unknown taxi route: {route_id}")
            return None

        dispatch = {
            "route_id": route_id,
            "origin": route["origin"],
            "dest": route["dest"],
            "eta_min": route["eta_min"],
            "passenger_count": passenger_count,
            "dispatched_at": datetime.now().isoformat(),
            "status": "En Route",
        }
        print(
            f"[+] Taxi {route_id}: {route['origin']} -> {route['dest']} "
            f"(ETA {route['eta_min']} min, pax={passenger_count})"
        )
        return dispatch

    def print_status_matrix(self):
        print("\n--- LOGISTICS STATUS MATRIX ---")
        print("Contractors:")
        for cid, c in self.CONTRACTOR_POOL.items():
            print(f"  [{cid}] {c['name']}: {c['status']} (crew={c['crew']})")
        print(f"Active allocations: {len(self.allocations)}")
        print(f"Procurement queue:  {len(self.procurement_queue)}")
        print("Taxi routes:")
        for rid, r in self.TAXI_ROUTES.items():
            print(f"  [{rid}] {r['origin']} -> {r['dest']} (ETA {r['eta_min']} min)")
        print("-------------------------------\n")

    def export_state(self, output_path):
        state = {
            "contractors": self.CONTRACTOR_POOL,
            "allocations": self.allocations,
            "procurement_queue": self.procurement_queue,
            "taxi_routes": self.TAXI_ROUTES,
            "exported_at": datetime.now().isoformat(),
        }
        with open(output_path, "w", encoding="utf-8") as fh:
            json.dump(state, fh, indent=2)
        print(f"[+] Logistics state exported: {output_path}")
        return state


if __name__ == "__main__":
    matrix = LogisticsMatrix()
    matrix.assign_contractor("JOB-04901-DECK", "MEC-001", "structural_lumber", units=120)
    matrix.queue_procurement("SS-FASTENER-3IN", 500, priority="HIGH")
    matrix.dispatch_taxi("TAXI-04901-A")
    matrix.print_status_matrix()
