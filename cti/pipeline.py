#!/usr/bin/env python3
"""
Sovereign CTI Passive Pipeline — CertStream → DoH → SQLite
Targets UNC5792/UNC4221 infrastructure patterns (passive only).
"""

import asyncio
import json
import logging
import re
import sqlite3
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

import tldextract

try:
    from cti.config import (
        ALERT_LOG,
        CERTSTREAM_URL,
        DB_PATH,
        GEOIP_ASN_PATH,
        SCHEMA_PATH,
        TARGET_KEYWORDS,
        WATCHLIST_PATH,
    )
except ImportError:
    from config import (
        ALERT_LOG,
        CERTSTREAM_URL,
        DB_PATH,
        GEOIP_ASN_PATH,
        SCHEMA_PATH,
        TARGET_KEYWORDS,
        WATCHLIST_PATH,
    )

logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(message)s")

try:
    import aiohttp
except ImportError:
    aiohttp = None

try:
    import websockets
except ImportError:
    websockets = None

try:
    import maxminddb
except ImportError:
    maxminddb = None


def init_database():
    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        conn.commit()


def load_watchlist():
    if not WATCHLIST_PATH.exists():
        return set(), [], [], {}
    data = json.loads(WATCHLIST_PATH.read_text(encoding="utf-8"))
    bad_asns = {str(k) for k in data.get("high_risk_asns", {})}
    bad_keywords = [kw.lower() for kw in data.get("high_risk_org_keywords", [])]
    patterns = [re.compile(p, re.I) for p in data.get("threat_patterns", [])]
    actor_tags = data.get("actor_tags", {})
    return bad_asns, bad_keywords, patterns, actor_tags


def infer_actor_tag(domain: str, actor_tags: dict) -> str | None:
    domain_lower = domain.lower()
    for tag, meta in actor_tags.items():
        for kw in meta.get("keywords", []):
            if kw in domain_lower:
                return tag
    return None


class SovereignPipeline:
    def __init__(self):
        self.queue = asyncio.Queue(maxsize=10000)
        self.seen_cache = deque(maxlen=50000)
        self.doh_semaphore = asyncio.Semaphore(10)
        self.bad_asns, self.bad_keywords, self.patterns, self.actor_tags = load_watchlist()
        self.asn_reader = None
        if maxminddb and GEOIP_ASN_PATH.exists():
            self.asn_reader = maxminddb.open_database(str(GEOIP_ASN_PATH))
        elif not GEOIP_ASN_PATH.exists():
            logging.warning("GeoLite2-ASN.mmdb missing — ASN mapping disabled")

    def _matches(self, domain: str) -> bool:
        domain_lower = domain.lower()
        if any(kw in domain_lower for kw in TARGET_KEYWORDS):
            return True
        return any(p.search(domain_lower) for p in self.patterns)

    def _is_known_bad(self, asn_num: str | None, asn_org: str | None) -> int:
        if asn_num and asn_num in self.bad_asns:
            return 1
        if asn_org:
            org_lower = asn_org.lower()
            if any(kw in org_lower for kw in self.bad_keywords):
                return 1
        return 0

    async def fetch_doh(self, domain: str) -> list[str]:
        if not aiohttp:
            return []
        async with self.doh_semaphore:
            url = f"https://cloudflare-dns.com/dns-query?name={domain}&type=A"
            headers = {"Accept": "application/dns-json"}
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        url, headers=headers, timeout=aiohttp.ClientTimeout(total=5)
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            return [
                                ans["data"]
                                for ans in data.get("Answer", [])
                                if ans.get("type") == 1
                            ]
            except Exception as e:
                logging.debug("DoH error %s: %s", domain, e)
            return []

    async def enrich_and_store(self, domain: str):
        ext = tldextract.extract(domain)
        registered = ext.registered_domain
        actor = infer_actor_tag(domain, self.actor_tags)
        ips = await self.fetch_doh(domain)

        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR IGNORE INTO domains (domain, registered_domain, actor_tag) VALUES (?, ?, ?)",
                (domain, registered, actor),
            )

            if not ips:
                conn.commit()
                return

            for ip in set(ips):
                asn_num = asn_org = None
                if self.asn_reader:
                    try:
                        geo = self.asn_reader.get(ip)
                        if geo:
                            asn_num = str(geo.get("autonomous_system_number"))
                            asn_org = geo.get("autonomous_system_organization")
                    except Exception:
                        pass

                risk_flag = self._is_known_bad(asn_num, asn_org)
                cursor.execute(
                    """
                    INSERT INTO resolutions (domain, ip_address, asn_number, asn_org, risk_flag)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(domain, ip_address) DO UPDATE SET
                        asn_number = excluded.asn_number,
                        asn_org = excluded.asn_org,
                        risk_flag = excluded.risk_flag,
                        first_seen = CURRENT_TIMESTAMP
                    """,
                    (domain, ip, asn_num, asn_org, risk_flag),
                )
                if risk_flag:
                    logging.warning(
                        "[RISK] %s → %s (%s AS%s) actor=%s",
                        domain, ip, asn_org, asn_num, actor or "unknown",
                    )
            conn.commit()

    def _append_alert(self, payload: dict):
        payload["logged_at"] = datetime.now(timezone.utc).isoformat()
        with open(ALERT_LOG, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload) + "\n")

    async def consumer(self):
        if not websockets:
            logging.error("websockets not installed — pip install websockets")
            return

        backoff = 1
        while True:
            try:
                logging.info("Connecting to CertStream...")
                async with websockets.connect(
                    CERTSTREAM_URL,
                    ping_interval=20,
                    ping_timeout=15,
                    max_size=2**21,
                ) as ws:
                    backoff = 1
                    async for raw_msg in ws:
                        msg = json.loads(raw_msg)
                        if msg.get("message_type") != "certificate_update":
                            continue
                        for domain in msg["data"]["leaf_cert"]["all_domains"]:
                            if domain.startswith("*."):
                                domain = domain[2:]
                            if self._matches(domain.lower()):
                                try:
                                    self.queue.put_nowait(domain.lower())
                                except asyncio.QueueFull:
                                    logging.warning("Queue full — dropping telemetry")
            except Exception as e:
                logging.error("WebSocket error: %s — retry in %ss", e, backoff)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 60)

    async def processor(self):
        while True:
            domain = await self.queue.get()
            try:
                if domain in self.seen_cache:
                    continue
                self.seen_cache.append(domain)

                ext = tldextract.extract(domain)
                if not any(
                    kw in (ext.domain or "") or kw in (ext.subdomain or "")
                    for kw in TARGET_KEYWORDS
                ) and not any(p.search(domain) for p in self.patterns):
                    continue

                logging.info("[MATCH] %s", domain)
                self._append_alert({
                    "domain": domain,
                    "registered_domain": ext.registered_domain,
                    "subdomain": ext.subdomain,
                    "source": "certstream",
                })
                asyncio.create_task(self.enrich_and_store(domain))
            finally:
                self.queue.task_done()

    async def start(self):
        init_database()
        await asyncio.gather(self.consumer(), self.processor())


def get_db_stats() -> dict:
    if not DB_PATH.exists():
        return {"domains": 0, "resolutions": 0, "wallets": 0, "high_risk": 0}
    with sqlite3.connect(DB_PATH) as conn:
        domains = conn.execute("SELECT COUNT(*) FROM domains").fetchone()[0]
        resolutions = conn.execute("SELECT COUNT(*) FROM resolutions").fetchone()[0]
        wallets = conn.execute("SELECT COUNT(*) FROM wallets").fetchone()[0]
        high_risk = conn.execute(
            "SELECT COUNT(*) FROM resolutions WHERE risk_flag = 1"
        ).fetchone()[0]
    return {
        "domains": domains,
        "resolutions": resolutions,
        "wallets": wallets,
        "high_risk": high_risk,
        "db_path": str(DB_PATH),
    }


def main():
    if not websockets or not aiohttp:
        print("[!] Install: pip install websockets aiohttp tldextract")
        raise SystemExit(1)
    pipeline = SovereignPipeline()
    try:
        asyncio.run(pipeline.start())
    except KeyboardInterrupt:
        logging.info("Sovereign CTI pipeline shutdown.")


if __name__ == "__main__":
    main()
