"""
Official-source-first retrieval layer for threat engine v2.
"""
import os
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

from app.config import config
from app.models.threat_schema import EvidenceItem
from app.services.scam_intelligence import scam_intelligence


@dataclass
class RetrievalResult:
    status: str
    corroborated: bool
    confidence: float
    evidence: List[EvidenceItem] = field(default_factory=list)
    reason_codes: List[str] = field(default_factory=list)


class RetrievalEngine:
    OFFICIAL_ORG_HINTS: Dict[str, Dict[str, str]] = {
        "lhdn": {
            "org": "LHDN",
            "website": "https://www.hasil.gov.my/",
            "hotline": "1-800-88-5436",
        },
        "bank negara": {
            "org": "Bank Negara Malaysia",
            "website": "https://www.bnm.gov.my/",
            "hotline": "1-300-88-5465",
        },
        "bnm": {
            "org": "Bank Negara Malaysia",
            "website": "https://www.bnm.gov.my/",
            "hotline": "1-300-88-5465",
        },
        "pdrm": {
            "org": "PDRM",
            "website": "https://www.rmp.gov.my/",
            "hotline": "03-2266 2222",
        },
        "police": {
            "org": "PDRM",
            "website": "https://www.rmp.gov.my/",
            "hotline": "03-2266 2222",
        },
        "maybank": {
            "org": "Maybank",
            "website": "https://www.maybank2u.com.my/",
            "hotline": "1-300-88-6688",
        },
        "cimb": {
            "org": "CIMB",
            "website": "https://www.cimb.com.my/",
            "hotline": "03-6204 7788",
        },
        "rhb": {
            "org": "RHB",
            "website": "https://www.rhbgroup.com/",
            "hotline": "03-9206 8118",
        },
    }

    def __init__(self, timeout_seconds: Optional[float] = None):
        self.timeout_seconds = timeout_seconds or config.RETRIEVAL_TIMEOUT_SECONDS
        self.allow_tier2 = config.THREAT_ENGINE_ALLOW_TIER2

    def _rank_url_tier(self, url: Optional[str]) -> int:
        if not url:
            return 3
        try:
            domain = (urlparse(url).netloc or "").lower()
        except Exception:
            return 3
        if any(
            token in domain
            for token in (
                ".gov.my",
                "bnm.gov.my",
                "rmp.gov.my",
                "hasil.gov.my",
                "maybank2u.com.my",
                "cimb.com.my",
                "rhbgroup.com",
            )
        ):
            return 1
        if any(token in domain for token in ("thestar.com.my", "nst.com.my", "malaymail.com")):
            return 2
        return 3

    def rank_source_tier(self, url: Optional[str]) -> int:
        return self._rank_url_tier(url)

    def _infer_org(self, claimed_organization: Optional[str], transcript: str) -> Optional[Tuple[str, Dict[str, str]]]:
        joined = f"{claimed_organization or ''} {transcript or ''}".lower()
        for key, meta in self.OFFICIAL_ORG_HINTS.items():
            if key in joined:
                return key, meta
        return None

    def _run_verify(self, org_name: str, caller_number: Optional[str]) -> Dict:
        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(
            scam_intelligence.verify_organization,
            org_name,
            caller_number,
        )
        try:
            return future.result(timeout=self.timeout_seconds)
        except TimeoutError:
            future.cancel()
            raise
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

    @staticmethod
    def _classify_error(error_text: str) -> str:
        low = (error_text or "").lower()
        if "resource_exhausted" in low or "quota exceeded" in low or "429" in low:
            return "retrieval_quota_exhausted"
        if "winerror 10061" in low or "actively refused" in low:
            proxy_values = [
                os.getenv("HTTP_PROXY") or "",
                os.getenv("HTTPS_PROXY") or "",
                os.getenv("ALL_PROXY") or "",
                os.getenv("http_proxy") or "",
                os.getenv("https_proxy") or "",
                os.getenv("all_proxy") or "",
            ]
            if any("127.0.0.1:9" in value for value in proxy_values):
                return "retrieval_proxy_refused"
            return "retrieval_connection_refused"
        if "timeout" in low or "timed out" in low:
            return "retrieval_timeout"
        return "retrieval_error"

    def verify(
        self,
        transcript: str,
        claimed_organization: Optional[str] = None,
        caller_number: Optional[str] = None,
    ) -> RetrievalResult:
        evidence: List[EvidenceItem] = []
        reason_codes: List[str] = []
        inferred = self._infer_org(claimed_organization, transcript)

        if inferred:
            _, meta = inferred
            evidence.append(
                EvidenceItem(
                    source=meta["org"],
                    source_tier=1,
                    title=f"Official verification channel for {meta['org']}",
                    summary=f"Use official website/hotline: {meta['website']} | {meta['hotline']}",
                    url=meta["website"],
                    supports_risk=False,
                    timestamp=datetime.utcnow().isoformat(),
                )
            )

        if not inferred and not claimed_organization:
            return RetrievalResult(
                status="skipped_no_org",
                corroborated=False,
                confidence=0.0,
                evidence=evidence,
                reason_codes=reason_codes,
            )

        org_name = (claimed_organization or inferred[1]["org"] if inferred else "").strip()
        if not org_name:
            return RetrievalResult(
                status="skipped_no_org",
                corroborated=False,
                confidence=0.0,
                evidence=evidence,
                reason_codes=reason_codes,
            )

        proxy_values = [
            os.getenv("HTTP_PROXY") or "",
            os.getenv("HTTPS_PROXY") or "",
            os.getenv("ALL_PROXY") or "",
            os.getenv("http_proxy") or "",
            os.getenv("https_proxy") or "",
            os.getenv("all_proxy") or "",
        ]
        if any("127.0.0.1:9" in value for value in proxy_values):
            reason_codes.append("retrieval_proxy_refused")
            evidence.append(
                EvidenceItem(
                    source="retrieval_engine",
                    source_tier=3,
                    title="Retrieval blocked by proxy",
                    summary="HTTP(S)_PROXY points to 127.0.0.1:9, which refuses connections.",
                    supports_risk=False,
                    timestamp=datetime.utcnow().isoformat(),
                )
            )
            return RetrievalResult(
                status="error",
                corroborated=False,
                confidence=0.0,
                evidence=evidence,
                reason_codes=reason_codes,
            )

        # Legacy SDK calls may block unpredictably under constrained networking.
        # Fall back to degraded mode rather than stalling live call analysis.
        if config.GEMINI_API_KEY:
            try:
                scam_intelligence._configure()
                if getattr(scam_intelligence.client, "sdk_name", "legacy") != "genai":
                    reason_codes.append("retrieval_degraded_legacy_sdk")
                    return RetrievalResult(
                        status="timeout",
                        corroborated=False,
                        confidence=0.0,
                        evidence=evidence,
                        reason_codes=reason_codes,
                    )
            except Exception:
                reason_codes.append("retrieval_unavailable")
                return RetrievalResult(
                    status="error",
                    corroborated=False,
                    confidence=0.0,
                    evidence=evidence,
                    reason_codes=reason_codes,
                )

        try:
            verification = self._run_verify(org_name, caller_number)
            if isinstance(verification, dict) and verification.get("error"):
                error_text = str(verification.get("error"))
                reason_codes.append(self._classify_error(error_text))
                evidence.append(
                    EvidenceItem(
                        source="retrieval_engine",
                        source_tier=3,
                        title="Retrieval failed",
                        summary=f"Retrieval error: {error_text}",
                        supports_risk=False,
                        timestamp=datetime.utcnow().isoformat(),
                    )
                )
                return RetrievalResult(
                    status="error",
                    corroborated=False,
                    confidence=0.0,
                    evidence=evidence,
                    reason_codes=reason_codes,
                )
            url = verification.get("official_website")
            tier = self._rank_url_tier(url)
            if tier <= 2:
                evidence.append(
                    EvidenceItem(
                        source=org_name,
                        source_tier=tier,
                        title=f"{org_name} legitimacy check",
                        summary=verification.get(
                            "verification_method",
                            "Verification response received.",
                        ),
                        url=url,
                        supports_risk=False,
                        timestamp=datetime.utcnow().isoformat(),
                    )
                )
            warning = verification.get("scam_warning") or ""
            number_verified = verification.get("number_verified")
            mismatch = number_verified is False
            if mismatch:
                reason_codes.append("retrieval_number_mismatch")
                evidence.append(
                    EvidenceItem(
                        source=org_name,
                        source_tier=max(1, tier),
                        title=f"Caller number mismatch for {org_name}",
                        summary="Caller number does not match organization official channels.",
                        url=url,
                        supports_risk=True,
                        timestamp=datetime.utcnow().isoformat(),
                    )
                )
            if warning:
                evidence.append(
                    EvidenceItem(
                        source=org_name,
                        source_tier=max(1, tier),
                        title=f"Scam warning for {org_name}",
                        summary=str(warning),
                        url=url,
                        supports_risk=True,
                        timestamp=datetime.utcnow().isoformat(),
                    )
                )
                reason_codes.append("retrieval_scam_warning")

            tier1_support = any(item.supports_risk and item.source_tier == 1 for item in evidence)
            tier2_support = any(item.supports_risk and item.source_tier == 2 for item in evidence)
            corroborated = tier1_support or (self.allow_tier2 and tier2_support)
            confidence = 0.85 if tier1_support else 0.65 if (self.allow_tier2 and tier2_support) else 0.35
            return RetrievalResult(
                status="ok",
                corroborated=corroborated,
                confidence=confidence,
                evidence=evidence,
                reason_codes=reason_codes,
            )
        except TimeoutError:
            reason_codes.append("retrieval_timeout")
            return RetrievalResult(
                status="timeout",
                corroborated=False,
                confidence=0.0,
                evidence=evidence,
                reason_codes=reason_codes,
            )
        except Exception as exc:
            mapped = self._classify_error(str(exc))
            reason_codes.append(mapped)
            evidence.append(
                EvidenceItem(
                    source="retrieval_engine",
                    source_tier=3,
                    title="Retrieval failed",
                    summary=f"Retrieval error ({mapped}): {exc}",
                    supports_risk=False,
                    timestamp=datetime.utcnow().isoformat(),
                )
            )
            return RetrievalResult(
                status="error",
                corroborated=False,
                confidence=0.0,
                evidence=evidence,
                reason_codes=reason_codes,
            )


retrieval_engine = RetrievalEngine()
