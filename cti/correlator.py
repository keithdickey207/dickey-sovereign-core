#!/usr/bin/env python3
"""
Sovereign CTI — Ollama RAG correlation engine (local-first).
"""

import json
from pathlib import Path

try:
    from cti.config import RAG_DIR
except ImportError:
    from config import RAG_DIR

try:
    import ollama
except ImportError:
    ollama = None


SYSTEM_PROMPT = """You are an elite CTI analyst for a sovereign, air-gapped defensive pipeline.
You analyze infrastructure overlap for Russian-aligned clusters UNC5792 and UNC4221.
Focus on: shared ASNs, domain naming patterns (signal/whatsapp/kropyva backup-key lures),
wallet funding overlaps, and MSK operational rhythm patterns.
Only use provided context. Flag actionable IOCs suitable for law enforcement submission.
Do not recommend offensive actions, honeypot injection, or unauthorized server access."""


def load_recent_context(days: int = 7) -> str:
    """Load latest RAG markdown summaries."""
    if not RAG_DIR.exists():
        return ""

    files = sorted(RAG_DIR.glob("infra_summary_*.md"), reverse=True)
    chunks = []
    for path in files[:days]:
        chunks.append(f"--- {path.name} ---\n{path.read_text(encoding='utf-8')}")
    return "\n\n".join(chunks)


def correlate(query: str, model: str = "llama3", window_files: int = 3) -> str:
    if not ollama:
        return "[!] ollama not installed"

    context = load_recent_context(window_files)
    if not context:
        return "[!] No RAG context — run: python3 graph_rag.py"

    prompt = f"""Context (local CTI graph summaries):
{context[:120000]}

Analyst query: {query}

Provide structured analysis:
1. Infrastructure clusters (IPs, ASNs, domains)
2. Actor attribution confidence (UNC5792 / UNC4221 / unknown)
3. Financial indicators (wallets, funding patterns)
4. Recommended IOCs for official submission (RFJ/FBI/CISA)
"""

    response = ollama.chat(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    )
    return response["message"]["content"]


def generate_rf_report(output_path: str = None) -> str:
    """Structured intelligence report for secure upstream submission."""
    query = (
        "Generate a structured CTI report listing all high-risk multiplexed infrastructure, "
        "associated domains, ASN details, wallet addresses, and operational timing patterns. "
        "Format for law enforcement tip submission — facts only, no speculation."
    )
    report = correlate(query)
    if output_path:
        Path(output_path).write_text(report, encoding="utf-8")
    return report


if __name__ == "__main__":
    import sys
    q = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else (
        "Identify infrastructure overlap suggesting UNC4221 campaign expansion in last 7 days."
    )
    print(correlate(q))
