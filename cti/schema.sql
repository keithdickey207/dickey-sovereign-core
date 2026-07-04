-- Sovereign CTI Passive Pipeline — Local-First Schema
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS domains (
    domain TEXT PRIMARY KEY,
    registered_domain TEXT NOT NULL,
    first_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
    risk_flag INTEGER DEFAULT 0,
    actor_tag TEXT,
    kit_signature TEXT
);

CREATE TABLE IF NOT EXISTS resolutions (
    domain TEXT NOT NULL,
    ip_address TEXT NOT NULL,
    asn_number TEXT,
    asn_org TEXT,
    first_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
    risk_flag INTEGER DEFAULT 0,
    PRIMARY KEY (domain, ip_address),
    FOREIGN KEY(domain) REFERENCES domains(domain) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS kit_signatures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    domain TEXT,
    signature_hash TEXT,
    wallet_addresses TEXT,
    unique_strings TEXT,
    source TEXT DEFAULT 'passive',
    first_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(domain) REFERENCES domains(domain)
);

CREATE TABLE IF NOT EXISTS wallets (
    address TEXT PRIMARY KEY,
    chain TEXT DEFAULT 'unknown',
    first_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
    linked_domain TEXT,
    risk_flag INTEGER DEFAULT 0,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS wallet_edges (
    src TEXT NOT NULL,
    dst TEXT NOT NULL,
    tx_id TEXT,
    amount REAL,
    timestamp TEXT,
    PRIMARY KEY (src, dst, tx_id),
    FOREIGN KEY(src) REFERENCES wallets(address),
    FOREIGN KEY(dst) REFERENCES wallets(address)
);

CREATE INDEX IF NOT EXISTS idx_res_ip ON resolutions(ip_address);
CREATE INDEX IF NOT EXISTS idx_res_asn ON resolutions(asn_number);
CREATE INDEX IF NOT EXISTS idx_dom_reg ON domains(registered_domain);
CREATE INDEX IF NOT EXISTS idx_wallets_domain ON wallets(linked_domain);