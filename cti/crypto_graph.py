#!/usr/bin/env python3
"""
Sovereign CTI — Crypto wallet ledger graphing (local-first, passive).
"""

import json
import re
import sqlite3
from datetime import datetime, timezone

try:
    from cti.config import DB_PATH
except ImportError:
    from config import DB_PATH

# Passive extraction patterns from kit/page analysis
WALLET_PATTERNS = {
    "btc": re.compile(r"\b(bc1|[13])[a-zA-HJ-NP-Z0-9]{25,62}\b"),
    "eth": re.compile(r"\b0x[a-fA-F0-9]{40}\b"),
}


def init_wallets_from_text(text: str, linked_domain: str = None) -> list[str]:
    """Extract wallet addresses from phishing kit strings or advisories."""
    found = []
    for chain, pattern in WALLET_PATTERNS.items():
        for match in pattern.findall(text):
            addr = match if isinstance(match, str) else match[0]
            if chain == "btc" and not addr.startswith(("1", "3", "bc1")):
                continue
            found.append((addr, chain))
    return found


def ingest_wallet(address: str, chain: str = "unknown", linked_domain: str = None, notes: str = None):
    if not DB_PATH.exists():
        raise FileNotFoundError("CTI database not initialized — run pipeline first")

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO wallets (address, chain, linked_domain, notes)
            VALUES (?, ?, ?, ?)
            """,
            (address, chain, linked_domain, notes),
        )
        conn.commit()


def ingest_transaction(src: str, dst: str, tx_id: str, amount: float = None, timestamp: str = None):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("INSERT OR IGNORE INTO wallets (address) VALUES (?)", (src,))
        conn.execute("INSERT OR IGNORE INTO wallets (address) VALUES (?)", (dst,))
        conn.execute(
            """
            INSERT OR IGNORE INTO wallet_edges (src, dst, tx_id, amount, timestamp)
            VALUES (?, ?, ?, ?, ?)
            """,
            (src, dst, tx_id, amount, timestamp or datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()


def build_graph_report() -> dict:
    """Build wallet flow graph — NetworkX if available, else adjacency list."""
    if not DB_PATH.exists():
        return {"nodes": 0, "edges": 0, "chokepoints": []}

    with sqlite3.connect(DB_PATH) as conn:
        wallets = conn.execute("SELECT address, chain, linked_domain FROM wallets").fetchall()
        edges = conn.execute("SELECT src, dst, tx_id, amount FROM wallet_edges").fetchall()

    try:
        import networkx as nx

        g = nx.DiGraph()
        for addr, chain, domain in wallets:
            g.add_node(addr, chain=chain, domain=domain)
        for src, dst, tx_id, amount in edges:
            g.add_edge(src, dst, tx_id=tx_id, amount=amount)

        in_degree = dict(g.in_degree())
        chokepoints = sorted(
            [(n, d) for n, d in in_degree.items() if d >= 2],
            key=lambda x: x[1],
            reverse=True,
        )[:10]

        return {
            "nodes": g.number_of_nodes(),
            "edges": g.number_of_edges(),
            "chokepoints": [{"address": n, "inbound_tx_count": d} for n, d in chokepoints],
            "backend": "networkx",
        }
    except ImportError:
        inbound = {}
        for src, dst, _, _ in edges:
            inbound[dst] = inbound.get(dst, 0) + 1
        chokepoints = sorted(inbound.items(), key=lambda x: x[1], reverse=True)[:10]
        return {
            "nodes": len(wallets),
            "edges": len(edges),
            "chokepoints": [{"address": n, "inbound_tx_count": d} for n, d in chokepoints],
            "backend": "stdlib",
        }


def ingest_kit_file(kit_path: str, domain: str = None):
    """Passive kit analysis — extract wallets and store kit signature."""
    from pathlib import Path
    import hashlib

    text = Path(kit_path).read_text(encoding="utf-8", errors="ignore")
    sig = hashlib.sha256(text.encode()).hexdigest()[:16]
    wallets = init_wallets_from_text(text, domain)

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO kit_signatures (domain, signature_hash, wallet_addresses, unique_strings, source)
            VALUES (?, ?, ?, ?, 'passive_kit')
            """,
            (domain, sig, json.dumps([w[0] for w in wallets]), text[:500]),
        )
        for addr, chain in wallets:
            conn.execute(
                "INSERT OR IGNORE INTO wallets (address, chain, linked_domain) VALUES (?, ?, ?)",
                (addr, chain, domain),
            )
        conn.commit()

    print(f"[+] Kit signature {sig} | wallets found: {len(wallets)}")
    return {"signature": sig, "wallets": wallets}


if __name__ == "__main__":
    report = build_graph_report()
    print(json.dumps(report, indent=2))