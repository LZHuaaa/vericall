"""
Threat engine v2 schemas.
"""
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


THREAT_LEVELS = ("safe", "low", "medium", "high", "critical")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ThreatSignal:
    name: str
    score: float
    confidence: float
    active: bool
    details: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class EvidenceItem:
    source: str
    source_tier: int
    title: str
    summary: str
    url: Optional[str] = None
    supports_risk: bool = False
    timestamp: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        if not payload.get("timestamp"):
            payload["timestamp"] = _utc_now_iso()
        return payload


@dataclass
class ThreatAssessment:
    risk_level: str
    risk_score: float
    confidence: float
    reason_codes: List[str] = field(default_factory=list)
    recommended_actions: List[str] = field(default_factory=list)
    evidence_items: List[EvidenceItem] = field(default_factory=list)
    retrieval_status: str = "not_started"
    signals: List[ThreatSignal] = field(default_factory=list)
    mode: str = "normal"
    version: str = "threat-v2"
    call_action: str = "none"
    call_action_confidence: float = 0.0
    call_action_reason_codes: List[str] = field(default_factory=list)
    hangup_after_ms: Optional[int] = None
    timestamp: str = field(default_factory=_utc_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "risk_level": self.risk_level,
            "risk_score": round(float(self.risk_score), 4),
            "confidence": round(float(self.confidence), 4),
            "reason_codes": list(self.reason_codes),
            "recommended_actions": list(self.recommended_actions),
            "evidence_items": [item.to_dict() for item in self.evidence_items],
            "retrieval_status": self.retrieval_status,
            "signals": [signal.to_dict() for signal in self.signals],
            "mode": self.mode,
            "version": self.version,
            "call_action": self.call_action,
            "call_action_confidence": round(float(self.call_action_confidence), 4),
            "call_action_reason_codes": list(self.call_action_reason_codes),
            "hangup_after_ms": self.hangup_after_ms,
            "timestamp": self.timestamp,
        }


@dataclass
class ThreatLiveEvent:
    session_id: str
    timestamp: str
    transcript_delta: str
    caller_number: Optional[str] = None
    claimed_organization: Optional[str] = None
    deepfake_snapshot: Optional[Dict[str, Any]] = None
    language: Optional[str] = None
    silence_metrics: Optional[Dict[str, Any]] = None
    audio_window_id: Optional[str] = None

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "ThreatLiveEvent":
        return cls(
            session_id=str(payload.get("session_id", "")).strip(),
            timestamp=str(payload.get("timestamp", "")).strip()
            or _utc_now_iso(),
            transcript_delta=str(payload.get("transcript_delta", "")).strip(),
            caller_number=(
                str(payload["caller_number"]).strip()
                if payload.get("caller_number") is not None
                else None
            ),
            claimed_organization=(
                str(payload["claimed_organization"]).strip()
                if payload.get("claimed_organization") is not None
                else None
            ),
            deepfake_snapshot=payload.get("deepfake_snapshot"),
            language=(
                str(payload["language"]).strip()
                if payload.get("language") is not None
                else None
            ),
            silence_metrics=payload.get("silence_metrics") if isinstance(payload.get("silence_metrics"), dict) else None,
            audio_window_id=(
                str(payload["audio_window_id"]).strip()
                if payload.get("audio_window_id") is not None
                else None
            ),
        )


@dataclass
class ThreatSessionState:
    session_id: str
    transcript: str = ""
    latest_assessment: Optional[ThreatAssessment] = None
    evidence_timeline: List[Dict[str, Any]] = field(default_factory=list)
    call_policy_state: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_utc_now_iso)
    updated_at: str = field(default_factory=_utc_now_iso)
    finalized: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "transcript": self.transcript,
            "latest_assessment": (
                self.latest_assessment.to_dict() if self.latest_assessment else None
            ),
            "evidence_timeline": list(self.evidence_timeline),
            "call_policy_state": dict(self.call_policy_state),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "finalized": self.finalized,
        }
