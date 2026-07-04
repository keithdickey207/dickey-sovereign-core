"""Sovereign CTI path configuration."""

from pathlib import Path

CTI_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = CTI_ROOT.parent
DATA_DIR = PROJECT_ROOT / "data"
RAG_DIR = DATA_DIR / "rag_context"
DB_PATH = DATA_DIR / "sovereign_cti.db"
SCHEMA_PATH = CTI_ROOT / "schema.sql"
WATCHLIST_PATH = CTI_ROOT / "watchlist.json"
GEOIP_ASN_PATH = DATA_DIR / "GeoLite2-ASN.mmdb"
ALERT_LOG = DATA_DIR / "sovereign_phish_alerts.jsonl"

CERTSTREAM_URL = "wss://certstream.calidog.io/"
TARGET_KEYWORDS = frozenset({
    "signal", "whatsapp", "kropyva", "sgnl", "teneta",
    "backup", "verify", "secure-chat", "linkdevice",
})

for path in (DATA_DIR, RAG_DIR):
    path.mkdir(parents=True, exist_ok=True)