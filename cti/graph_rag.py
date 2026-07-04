#!/usr/bin/env python3
"""
Sovereign CTI — SQLite graph → Markdown RAG context export.
"""

import logging
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

try:
    from cti.config import DB_PATH, RAG_DIR
except ImportError:
    from config import DB_PATH, RAG_DIR

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def generate_infra_summary(window_days: int = 7) -> Path | None:
    if not DB_PATH.exists():
        logging.warning("No CTI database — run pipeline first")
        return None

    current_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    summary_file = RAG_DIR / f"infra_summary_{current_date}.md"
    window_param = f"-{window_days} days"

    multiplex_query = """
        SELECT r.ip_address, r.asn_number, r.asn_org,
               COUNT(DISTINCT d.registered_domain) AS domain_count,
               GROUP_CONCAT(DISTINCT d.domain) AS associated_domains,
               SUM(CASE WHEN r.risk_flag = 1 THEN 1 ELSE 0 END) AS risk_score
        FROM resolutions r
        JOIN domains d ON r.domain = d.domain
        WHERE r.first_seen >= datetime('now', ?)
        GROUP BY r.ip_address, r.asn_number, r.asn_org
        HAVING domain_count > 1 OR risk_score > 0
        ORDER BY risk_score DESC, domain_count DESC;
    """

    brand_query = """
        SELECT d.registered_domain, COUNT(d.domain) AS sub_count,
               GROUP_CONCAT(DISTINCT r.asn_org) AS providers,
               MAX(r.first_seen) AS latest_sighting,
               GROUP_CONCAT(DISTINCT d.actor_tag) AS actors
        FROM domains d
        LEFT JOIN resolutions r ON d.domain = r.domain
        WHERE d.first_seen >= datetime('now', ?)
        GROUP BY d.registered_domain
        ORDER BY sub_count DESC;
    """

    wallet_query = """
        SELECT address, chain, linked_domain, first_seen
        FROM wallets
        WHERE first_seen >= datetime('now', ?)
        ORDER BY first_seen DESC;
    """

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        params = [window_param]
        multiplexed = conn.execute(multiplex_query, params).fetchall()
        brands = conn.execute(brand_query, params).fetchall()
        wallets = conn.execute(wallet_query, params).fetchall()

    md = [
        f"# Sovereign CTI Infrastructure Graph Report — {current_date}",
        f"Generated: {datetime.now(timezone.utc).isoformat()} | Window: {window_days} days\n",
        "## [CRITICAL] Multiplexed & High-Risk Infrastructure\n",
    ]

    if not multiplexed:
        md.append("- No multiplexed or flagged infrastructure in window.\n")
    else:
        for row in multiplexed:
            md.extend([
                f"### Node: `{row['ip_address']}` (AS{row['asn_number']} — {row['asn_org']})",
                f"- Domain count: {row['domain_count']} | Risk score: {row['risk_score']}",
                "- Domains:",
            ])
            for dom in (row["associated_domains"] or "").split(","):
                if dom.strip():
                    md.append(f"  - `{dom.strip()}`")
            md.append("")

    md.append("## Target Brand & Provider Topology\n")
    for row in brands:
        md.append(
            f"- `{row['registered_domain']}` | subs={row['sub_count']} | "
            f"actors={row['actors'] or 'unattributed'} | latest={row['latest_sighting']}"
        )
        md.append(f"  - Providers: {row['providers'] or 'unresolved'}")

    md.append("\n## Crypto Wallet Sightings\n")
    if not wallets:
        md.append("- No wallet addresses ingested in window.\n")
    else:
        for w in wallets:
            md.append(f"- `{w['address']}` ({w['chain']}) linked to `{w['linked_domain']}`")

    msk_section = _msk_operational_rhythm(window_days)
    if msk_section:
        md.append("\n## Operational Rhythm (MSK Analysis)\n")
        md.extend(msk_section)

    summary_file.write_text("\n".join(md), encoding="utf-8")
    logging.info("RAG context written: %s", summary_file)
    return summary_file


def _msk_operational_rhythm(window_days: int) -> list[str]:
    """Passive timestamp analysis — behavioral fingerprint without touching adversary systems."""
    query = """
        SELECT strftime('%H', first_seen) AS hour_utc, COUNT(*) AS cnt
        FROM resolutions
        WHERE first_seen >= datetime('now', ?)
        GROUP BY hour_utc ORDER BY cnt DESC;
    """
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(query, [f"-{window_days} days"]).fetchall()
    if not rows:
        return []

    lines = ["Hourly activity distribution (UTC → add +3 for MSK estimate):"]
    for hour, cnt in rows[:8]:
        msk_hour = (int(hour) + 3) % 24
        lines.append(f"- {hour}:00 UTC ({msk_hour:02d}:00 MSK): {cnt} resolution events")
    return lines


if __name__ == "__main__":
    path = generate_infra_summary()
    if path:
        print(path.read_text(encoding="utf-8")[:2000])