"""
Unit tests for threat engine v2.
"""
import unittest

from app.models.schemas import RecommendedAction, ScamAnalysis, ScamType, UrgencyLevel
from app.models.threat_schema import EvidenceItem
from app.services.redaction import RedactionService
from app.services.retrieval_engine import RetrievalResult, RetrievalEngine
from app.services.threat_orchestrator import ThreatOrchestrator


class FakeAnalyzer:
    def __init__(self, is_scam: bool, confidence: float, scam_type: ScamType = ScamType.UNKNOWN):
        self.is_scam = is_scam
        self.confidence = confidence
        self.scam_type = scam_type

    def analyze_content_sync(self, transcript, deepfake_score, artifacts_detected):
        return ScamAnalysis(
            is_scam=self.is_scam,
            confidence=self.confidence,
            scam_type=self.scam_type,
            claimed_identity="caller",
            amount_requested="RM8000" if self.is_scam else None,
            urgency_level=UrgencyLevel.HIGH if self.is_scam else UrgencyLevel.LOW,
            red_flags=["asks for otp"] if self.is_scam else [],
            recommendation=RecommendedAction.VERIFY,
        )


class FakeRetrieval:
    def __init__(self, status: str, corroborated: bool, confidence: float):
        self.status = status
        self.corroborated = corroborated
        self.confidence = confidence

    def verify(self, transcript, claimed_organization=None, caller_number=None):
        evidence = []
        reason_codes = []
        if self.corroborated:
            evidence.append(
                EvidenceItem(
                    source="official",
                    source_tier=1,
                    title="Official mismatch found",
                    summary="Caller number mismatch with official records",
                    supports_risk=True,
                )
            )
            reason_codes.append("retrieval_number_mismatch")
        if self.status == "timeout":
            reason_codes.append("retrieval_timeout")
        return RetrievalResult(
            status=self.status,
            corroborated=self.corroborated,
            confidence=self.confidence,
            evidence=evidence,
            reason_codes=reason_codes,
        )


class ThreatEngineTests(unittest.TestCase):
    def test_redaction_masks_sensitive_fields(self):
        service = RedactionService()
        text = "My OTP 123456 and phone +6012-3456789 email a@b.com"
        redacted = service.redact_text(text)
        self.assertIn("[REDACTED_SECRET]", redacted)
        self.assertIn("[REDACTED_PHONE]", redacted)
        self.assertIn("[REDACTED_EMAIL]", redacted)

    def test_source_trust_ranking(self):
        engine = RetrievalEngine(timeout_seconds=0.1)
        self.assertEqual(engine.rank_source_tier("https://www.bnm.gov.my/"), 1)
        self.assertEqual(engine.rank_source_tier("https://www.thestar.com.my/"), 2)
        self.assertEqual(engine.rank_source_tier("https://random-forum.example/"), 3)

    def test_high_requires_two_independent_signals(self):
        orchestrator = ThreatOrchestrator(
            analyzer=FakeAnalyzer(is_scam=True, confidence=0.92, scam_type=ScamType.BANK),
            retrieval=FakeRetrieval(status="ok", corroborated=False, confidence=0.0),
        )
        result = orchestrator.assess_live(
            {
                "session_id": "s1",
                "timestamp": "2026-02-17T10:00:00Z",
                "transcript_delta": "I am from bank, give OTP now",
            }
        )
        self.assertIn(result["risk_level"], ("low", "medium"))
        self.assertNotIn(result["risk_level"], ("high", "critical"))
        self.assertIn("call_action", result)

    def test_critical_allows_strong_multisignal_consensus(self):
        orchestrator = ThreatOrchestrator(
            analyzer=FakeAnalyzer(is_scam=True, confidence=0.95, scam_type=ScamType.BANK),
            retrieval=FakeRetrieval(status="ok", corroborated=True, confidence=0.9),
        )
        result = orchestrator.assess_live(
            {
                "session_id": "s2",
                "timestamp": "2026-02-17T10:00:05Z",
                "transcript_delta": "Bank security call, share OTP now",
                "claimed_organization": "Maybank",
                "deepfake_snapshot": {
                    "score": 0.94,
                    "confidence": 0.9,
                    "artifacts": ["robotic cadence"],
                },
            }
        )
        self.assertIn(result["risk_level"], ("high", "critical"))
        self.assertGreaterEqual(result["risk_score"], 0.72)

    def test_timeout_sets_degraded_mode(self):
        orchestrator = ThreatOrchestrator(
            analyzer=FakeAnalyzer(is_scam=False, confidence=0.2),
            retrieval=FakeRetrieval(status="timeout", corroborated=False, confidence=0.0),
        )
        result = orchestrator.assess_live(
            {
                "session_id": "s3",
                "timestamp": "2026-02-17T10:00:10Z",
                "transcript_delta": "Hello there",
            }
        )
        self.assertEqual(result["mode"], "degraded_local")
        self.assertEqual(result["retrieval_status"], "timeout")
        self.assertIn("call_action", result)


if __name__ == "__main__":
    unittest.main()
