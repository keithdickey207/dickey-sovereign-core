#!/usr/bin/env python3
"""Bridge Dickey.OS Core to Sovereign CTI subsystem."""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from cti.pipeline import SovereignPipeline, get_db_stats, init_database
from cti.graph_rag import generate_infra_summary
from cti.crypto_graph import build_graph_report, ingest_kit_file
from cti.correlator import correlate, generate_rf_report
from cti.ops_math import print_ops_report


def run_cti_status():
    stats = get_db_stats()
    print("\n--- SOVEREIGN CTI STATUS ---")
    for key, val in stats.items():
        print(f"  {key}: {val}")
    print("----------------------------\n")
    return stats


def run_cti_rag(window_days: int = 7):
    path = generate_infra_summary(window_days=window_days)
    if path:
        print(f"[+] RAG context: {path}")
    return path


def run_cti_math():
    return print_ops_report()


def run_cti_correlate(query: str, model: str = "llama3"):
    result = correlate(query, model=model)
    print("\n--- CTI CORRELATION ---")
    print(result)
    print("-----------------------\n")
    return result


def run_cti_crypto_report():
    report = build_graph_report()
    print("\n--- CRYPTO GRAPH ---")
    import json
    print(json.dumps(report, indent=2))
    print("--------------------\n")
    return report