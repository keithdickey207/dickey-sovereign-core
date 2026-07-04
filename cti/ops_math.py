#!/usr/bin/env python3
"""
Sovereign CTI — Operational & Resource Mathematics
Validates hardware sizing for passive CertStream → Ollama pipeline.
"""

import math


def ingestion_math(
    certs_per_sec_avg: float = 350.0,
    certs_per_sec_peak: float = 1200.0,
    payload_kb: float = 1.5,
    decimation_rate: float = 0.00001,
    queue_maxsize: int = 10000,
) -> dict:
    """CertStream throughput and queue resilience."""
    filtered_per_hour_avg = certs_per_sec_avg * 3600 * decimation_rate
    filtered_per_hour_peak = certs_per_sec_peak * 3600 * decimation_rate
    ingress_mbps_peak = (certs_per_sec_peak * payload_kb * 8) / 1000
    queue_hold_sec_peak = queue_maxsize / max(certs_per_sec_peak * decimation_rate, 1e-9)

    return {
        "global_certs_per_sec_avg": certs_per_sec_avg,
        "global_certs_per_sec_peak": certs_per_sec_peak,
        "decimation_rate": decimation_rate,
        "decimation_factor": int(1 / decimation_rate),
        "filtered_domains_per_hour_avg": round(filtered_per_hour_avg, 2),
        "filtered_domains_per_hour_peak": round(filtered_per_hour_peak, 2),
        "ingress_mbps_peak": round(ingress_mbps_peak, 2),
        "queue_maxsize": queue_maxsize,
        "queue_buffer_seconds_at_peak_filter": round(queue_hold_sec_peak, 1),
        "queue_ram_mb_worst_case": round(queue_maxsize * payload_kb / 1024, 1),
    }


def enrichment_math(
    doh_concurrency: int = 10,
    doh_rtt_ms_avg: float = 100.0,
    domains_per_hour: float = 5.0,
) -> dict:
    """DoH enrichment compute bounds."""
    domains_per_sec = domains_per_hour / 3600
    max_throughput_dps = doh_concurrency / (doh_rtt_ms_avg / 1000)
    utilization = domains_per_sec / max_throughput_dps if max_throughput_dps else 0

    return {
        "doh_concurrency": doh_concurrency,
        "doh_rtt_ms_avg": doh_rtt_ms_avg,
        "domains_per_hour_assumed": domains_per_hour,
        "max_enrichment_domains_per_sec": round(max_throughput_dps, 2),
        "cpu_utilization_fraction": round(utilization, 6),
        "cpu_utilization_pct": round(utilization * 100, 4),
        "outbound_kb_per_day_estimate": round(domains_per_hour * 24 * 0.5, 1),
    }


def storage_math(
    domains_per_day: int = 100,
    ips_per_domain: float = 1.5,
    days: int = 365,
) -> dict:
    """SQLite growth projections."""
    domain_row_bytes = 160
    resolution_row_bytes = 280
    rows_per_day = domains_per_day * (1 + ips_per_domain)
    rows_year = rows_per_day * days
    bytes_year = domains_per_day * days * domain_row_bytes + (
        domains_per_day * ips_per_domain * days * resolution_row_bytes
    )

    return {
        "domains_per_day": domains_per_day,
        "ips_per_domain_avg": ips_per_domain,
        "rows_per_day": round(rows_per_day),
        "rows_per_year": round(rows_year),
        "storage_mb_per_year": round(bytes_year / (1024 * 1024), 2),
        "indexed_query_ms": "< 1",
    }


def rag_inference_math(
    markdown_kb_7day: float = 150.0,
    chars_per_token: float = 4.0,
    model_params_b: float = 8.0,
    quant_bits: float = 4.0,
    context_tokens: int = 32768,
) -> dict:
    """Local Ollama RAG context and VRAM estimates."""
    tokens = (markdown_kb_7day * 1024) / chars_per_token
    vram_gb = (model_params_b * quant_bits / 8) + (context_tokens * 0.00005)

    return {
        "markdown_kb_7day": markdown_kb_7day,
        "estimated_tokens": round(tokens),
        "context_window_tokens": context_tokens,
        "fits_context_window": tokens < context_tokens,
        "vram_gb_estimate": round(vram_gb, 2),
        "inference_tokens_per_sec_range": "25-60",
    }


def print_ops_report():
    ing = ingestion_math()
    enr = enrichment_math()
    sto = storage_math()
    rag = rag_inference_math()

    print("\n" + "=" * 60)
    print("  SOVEREIGN CTI — OPERATIONAL MATHEMATICS")
    print("=" * 60)

    print("\n[1] INGESTION (CertStream)")
    print(f"    Global rate: {ing['global_certs_per_sec_avg']:.0f} avg / {ing['global_certs_per_sec_peak']:.0f} peak certs/s")
    print(f"    Decimation: 1:{ing['decimation_factor']:,} → ~{ing['filtered_domains_per_hour_avg']:.1f} domains/hr avg")
    print(f"    Peak ingress: {ing['ingress_mbps_peak']:.1f} Mbps | Queue hold: {ing['queue_buffer_seconds_at_peak_filter']:.0f}s")

    print("\n[2] ENRICHMENT (DoH + MaxMind)")
    print(f"    Throughput ceiling: {enr['max_enrichment_domains_per_sec']:.1f} domains/s @ {enr['doh_concurrency']} concurrent")
    print(f"    CPU load @ 5 domains/hr: {enr['cpu_utilization_pct']:.4f}%")

    print("\n[3] STORAGE (SQLite)")
    print(f"    Annual rows: ~{sto['rows_per_year']:,} | Footprint: ~{sto['storage_mb_per_year']:.1f} MB")

    print("\n[4] RAG + OLLAMA")
    print(f"    7-day context: ~{rag['estimated_tokens']:,} tokens | VRAM: ~{rag['vram_gb_estimate']:.1f} GB")
    print("=" * 60 + "\n")

    return {"ingestion": ing, "enrichment": enr, "storage": sto, "rag": rag}


if __name__ == "__main__":
    print_ops_report()