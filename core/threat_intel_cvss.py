#!/usr/bin/env python3
"""
CVSS Threat Intelligence Pipeline — Sovereign Environmental Mitigation Scoring
Strictly Local Execution Protocol (no external API required for scoring)
"""

import json
import os
import sys

try:
    import ollama
except ImportError:
    ollama = None


class ThreatIntelCVSS:
    """Offline CVSS matrix and local LLM enrichment for sovereign architectures."""

    SEVERITY_BANDS = [
        (0.0, "NONE"),
        (0.1, "LOW"),
        (4.0, "MEDIUM"),
        (7.0, "HIGH"),
        (9.0, "CRITICAL"),
    ]

    def __init__(self, ai_model="llama3", enable_llm=True):
        self.ai_model = ai_model
        self.enable_llm = enable_llm and ollama is not None
        self.vault = []
        print("[*] Threat Intel CVSS pipeline initialized (air-gapped scoring)")

    def score_cvss_vector(self, vector_string):
        """
        Parse a CVSS:3.x vector and compute an approximate base score.
        Supports common exploitability + impact metrics without cloud lookup.
        """
        metrics = {}
        for part in vector_string.split("/"):
            if ":" in part:
                key, val = part.split(":", 1)
                metrics[key] = val

        av_map = {"N": 0.85, "A": 0.62, "L": 0.55, "P": 0.2}
        ac_map = {"L": 0.77, "H": 0.44}
        pr_map = {"N": 0.85, "L": 0.62, "H": 0.27}
        ui_map = {"N": 0.85, "S": 0.62}
        c_map = {"N": 0.0, "L": 0.22, "H": 0.56}
        i_map = {"N": 0.0, "L": 0.22, "H": 0.56}
        a_map = {"N": 0.0, "L": 0.22, "H": 0.56}

        scope_changed = metrics.get("S") == "C"
        isc = 1 - (1 - c_map.get(metrics.get("C", "N"), 0)) * (
            1 - i_map.get(metrics.get("I", "N"), 0)
        ) * (1 - a_map.get(metrics.get("A", "N"), 0))

        if scope_changed:
            exploitability = (
                8.22
                * av_map.get(metrics.get("AV", "N"), 0.85)
                * ac_map.get(metrics.get("AC", "L"), 0.77)
                * pr_map.get(metrics.get("PR", "N"), 0.85)
                * ui_map.get(metrics.get("UI", "N"), 0.85)
            )
            impact = 7.52 * (isc - 0.029) - 3.25 * pow(isc - 0.02, 15)
            if impact <= 0:
                base = 0.0
            else:
                base = min(10.0, 1.08 * (impact + exploitability))
        else:
            exploitability = (
                8.22
                * av_map.get(metrics.get("AV", "N"), 0.85)
                * ac_map.get(metrics.get("AC", "L"), 0.77)
                * pr_map.get(metrics.get("PR", "N"), 0.85)
                * ui_map.get(metrics.get("UI", "N"), 0.85)
            )
            impact = 6.42 * isc
            if impact <= 0:
                base = 0.0
            else:
                base = min(10.0, impact + exploitability)

        return round(base, 1)

    def severity_from_score(self, score):
        for threshold, label in reversed(self.SEVERITY_BANDS):
            if score >= threshold:
                return label
        return "NONE"

    def enrich_local_cve(self, cve_record):
        """Score and optionally enrich a local CVE JSON record offline."""
        cve_id = cve_record.get("cve_id") or cve_record.get("id", "CVE-UNKNOWN")
        vector = cve_record.get("cvss_vector") or cve_record.get("vectorString", "")

        if vector:
            score = self.score_cvss_vector(vector)
        else:
            score = float(cve_record.get("base_score", 0.0))

        severity = self.severity_from_score(score)
        enriched = {
            "cve_id": cve_id,
            "base_score": score,
            "severity": severity,
            "cvss_vector": vector,
            "vendor_product": cve_record.get("vendor_product", []),
            "executive_summary": cve_record.get("executive_summary", ""),
        }

        if self.enable_llm and not enriched["executive_summary"]:
            enriched["executive_summary"] = self._llm_summarize(enriched)

        self.vault.append(enriched)
        print(f"[+] {cve_id}: score={score} severity={severity}")
        return enriched

    def ingest_file(self, json_path):
        """Load a local CVE JSON file (single object or array) and score offline."""
        if not os.path.isfile(json_path):
            print(f"[!] CVE archive missing: {json_path}")
            return []

        with open(json_path, encoding="utf-8") as fh:
            data = json.load(fh)

        records = data if isinstance(data, list) else [data]
        return [self.enrich_local_cve(r) for r in records]

    def _llm_summarize(self, enriched):
        if not ollama:
            return "Local LLM unavailable — manual review required."

        try:
            response = ollama.chat(
                model=self.ai_model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an elite cybersecurity analyst for sovereign air-gapped systems. "
                            "Provide a 2-sentence plain-English threat summary and mitigation priority."
                        ),
                    },
                    {"role": "user", "content": json.dumps(enriched)},
                ],
            )
            return response["message"]["content"]
        except Exception as e:
            return f"LLM enrichment failed: {e}"

    def export_vault(self, output_path):
        with open(output_path, "w", encoding="utf-8") as fh:
            json.dump(self.vault, fh, indent=2)
        print(f"[+] Threat vault exported: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        demo = {
            "cve_id": "CVE-2026-04901",
            "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
            "vendor_product": ["Sovereign-Edge-Node"],
        }
        intel = ThreatIntelCVSS(enable_llm=False)
        intel.enrich_local_cve(demo)
    else:
        ThreatIntelCVSS().ingest_file(sys.argv[1])